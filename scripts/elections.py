import pyrankvote
import election_helper
from election_helper import get_candidates, get_ballots
from election_helper import PositionElection
from position_table import columns as pos_columns
from copy import copy

election_helper.MAX_POSITIONS = 3
election_helper.CANDIDATE_START_ROW = 9
election_helper.VOTING_START_ROW = 3

joints = [(["Kevin McKay", "Meg Slot"], ["Membership Chair"], "Kevin McKay and Megan Slot"),
          (["Zac Wirth", "Allen Zhao"], ["Trips Coordinator"], "Zac Wirth and Allen Zhao")]

elec_with_multi_seats = {"Quartermaster": 5}

# Add people who aren't on the position application form but are on the
# election here.
fill_ins = [election_helper.Candidate("Settare Shariati", ["Public Relations"],
                                      election_helper.Info("settare@zoology.ubc.ca", True, [1, 2]))]

# {<old>: <new>}
names_to_change = {"FMCBC/ACC Rep": "FMCBC/ACC Representative"}


def is_eligible(line):
    studentnum = line[17]
    if line[6] == "TRUE":  # check to see if survey was finished
        return True
    else:
        print("Rejected {}'s ballot: incomplete".format(studentnum))
        return False


candidates = get_candidates("../data/Nominee_March 15, 2023_13.03.csv",
                            joint_candidates=joints, nts=names_to_change)
for fill_in in fill_ins:
    candidates.update({fill_in.name: fill_in})

ballots = get_ballots("../data/TEST VOC Exec Election 2023.csv", pos_columns,
                      candidates, is_eligible)

# build dictionary of positions and their candidiates
candidates_by_pos = {}
for c in candidates.values():
    for pos in c.positions:
        if pos not in candidates_by_pos.keys():
            candidates_by_pos.update({pos: [c]})
        else:
            candidates_by_pos[pos].append(c)

print("Building elections:")

elections = []

for position in ballots.keys():
    pos_ballots = ballots[position]
    pos_candidates = candidates_by_pos[position]
    # handle elections with multiple seats.
    if position in elec_with_multi_seats.keys():
        seats = elec_with_multi_seats[position]
    else:
        seats = 1
    elec = PositionElection(position, pos_candidates, pos_ballots,
                            # evaluator_method=pyrankvote.single_transferable_vote,
                            # soooo it seems like preferential block voting can cause large ties
                            # think about maybe using STV instead?
                            seats=seats)
    print("\n" + str(elec))
    elections.append(elec)
print("...done")

all_elections = copy(elections)
complete = False
iteration = 1
final_winners = []
filter_priority = 1
problems = []
while not filter_priority > 3:
    no_new_winners = False
    while not (no_new_winners or filter_priority > 3):
        print("Running all elections... (iteration {}, ranking threshold {})"
              .format(iteration, filter_priority))
        # for each cycle:
        # build a list of winners, including what they won and their rankings
        cycle_winners = {}
        elections_to_remove = []
        reasons = []
        for election in elections:
            result = election.compute_winners()
            if result is None:
                problem = ("at (iteration {}, ranking threshold {})\n"
                           .format(iteration, filter_priority) +
                           "Nobody left to run for {} Original candidates: {}\n"
                           .format(election.position, list([c.name for c in election.starting])))
                problems.append(problem)
                elections_to_remove.append(election)
                reasons.append("no candidates")
                continue

            for winner, ranking in result:
                if winner not in cycle_winners.keys():
                    cycle_winners.update({winner: ([election], [ranking])})
                else:
                    cycle_winners[winner][0].append(election)
                    cycle_winners[winner][1].append(ranking)
        if len(cycle_winners) == 0:
            # skip processing if no new winners detected
            # then lower ranking threshold.
            no_new_winners = True
        # for each entry, pick the highest-ranked election won, finalize that one.
        # remove this person from all the other elections and their ballots.
        print("\n Computing true winners...")
        for candidate, wins, in cycle_winners.items():
            won_elecs, rankings = wins
            if filter_priority in rankings or (len(won_elecs) == 1 and len(won_elecs[0].candidates) == 1):
                if len(won_elecs) == 1:
                    won_election = won_elecs[0]
                    print("\n (FORCED) {} won {} as their #{} choice (final)..."
                          .format(candidate.name,
                                  won_election.position, rankings[0]))
                else:
                    won_election = won_elecs[rankings.index(filter_priority)]
                    print("\n{} won {} as their #{} choice (final)..."
                          .format(candidate.name,
                                  won_election.position, filter_priority))
                won_election.final_winners.append(candidate)
                print(candidate.name)
                # if this person ran in other elections, remove them from them.
                # or if they are a joint candidate (joint object not represnttive)
                if len(candidate.positions) > 1 or candidate.joint:
                    print("Removing them from other elections:")
                    for election in elections:
                        if election is not won_election:
                            if candidate.joint:
                                for subcandidate in candidate.joint_candidates:
                                    election.remove_candidate(subcandidate)
                            else:
                                election.remove_candidate(candidate)
                else:
                    print("This was their only election.")
        print("\n")
        for election in all_elections:
            print("{}: {}/{} seats filled.".format(
                election.position, len(election.final_winners), election.seats))
        print('\n')
        # allows us to remove items from a list we're iterating over
        elections_pre_removal = copy(elections)
        for election in elections_pre_removal:
            if len(election.final_winners) >= election.seats:
                print("All seats for {} election satisfied, closing..."
                      .format(election.position))
                elections.remove(election)
            elif election in elections_to_remove:
                reason = reasons[elections_to_remove.index(election)]
                print("Closing {} election due to {}"
                      .format(election.position, reason))
                elections.remove(election)

        filter_priority += 1

print("\n===FINAL ELECTION RESULTS===")
for election in all_elections:
    winners = election.final_winners
    print("\n")
    print(election.position + ":")
    if len(winners) == 1:
        print("{} ({})"
              .format(winners[0],
                      winners[0].info.email))
    elif len(winners) != 0:
        for winner in winners:
            print("{} ({})"
                  .format(winner,
                          winner.info.email))
        if len(winners) > election.seats:
            print("\n (More than {} seats filled due to a tie somewhere in the voting.)"
                .format(election.seats))

if len(problems) != 0:
    print("\n===ELECTION ISSUES===")

    for problem in problems:
        print(problem)

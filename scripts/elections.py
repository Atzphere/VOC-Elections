import pyrankvote
import election_helper
from election_helper import get_candidates, get_ballots
from election_helper import PositionElection
from position_table import columns as pos_columns
from copy import copy

# CONFIGURABLES

CANDIDACY_FILE = "../data/exec-nominees-2024-cleaned.csv"
BALLOT_FILE = "../data/exec-votes-2023.csv"

election_helper.MAX_POSITIONS = 3
election_helper.CANDIDATE_START_ROW = 1
election_helper.VOTING_START_ROW = 3

# CANDIDACY COLUMNS
# make sure your CSV has these columns, you can bullshit them if obsolete

# the really important columns you 100% should have:
# qualtrics is dumb so we have to join names. if the names are pre-joined,
# put the full name in the surname column and leave the firstname column empy.
election_helper.SURNAME_COL = 0
election_helper.FIRSTNAME_COL = 1
election_helper.EMAIL_COL = 5
election_helper.ROLES_COL = 2 # the roles the candidate is running for, separated by commas.
# i.e.: "Legacy Coordinator,Journal Editor,Membership Chair"

# the somewhat obsolete columns you can definitely bullshit
# was used for candidate filtering
election_helper.STATUS_COL = 6 # student status for candidate validation, approved value: "Yes"
election_helper.CAND_TYPE_COL = 7 # literally anything other than "Survey Preview" will pass the candidate
election_helper.TERMS_COL = 8 # the terms the candidate will be a student for. approved value: "Term 1,Term 2"

# BALLOT VALIDATION
FINISHED_SURVEY_COLUMN = 6 # to filter incomplete/unsubmitted ballots
STUDENTNUM_COLUMN = 17 # student number column

# if someone has already gone through and checked eligibility and all you have is raw vote data, use this.
USE_RAW_VOTING_INFO = True
RAW_VOTING_OFFSET = -18  # offset the column designations in VOTING.csv.

# write in joint candidates here, moving on we're trying to avoid this (2024)

joints = [(["Homer Simpson", "Lenny Leonard"], ["Donut Coordinator"], "Homer Simpson and Lenny Leonard")]

# elections with multiple seats, i.e. always quartermasters...

elec_with_multi_seats = {"Quartermaster": 5}

# Add people who aren't on the candidate form but are on the election here.
fill_ins = [election_helper.Candidate("Monty Burns", ["Director"],
                                      election_helper.Info("burns@springfieldpower.com", True, [1, 2]))]

# put naming discrepancies between the candidate form and election form here
# {<old>: <new>}
names_to_change = {"FMCBC/ACC Rep": "FMCBC/ACC Representative"}


# END CONFIGURABLES


def is_eligible(line):
    studentnum = line[STUDENTNUM_COLUMN]
    if line[FINISHED_SURVEY_COLUMN] == "TRUE":  # check to see if survey was finished
        return True
    else:
        print(f"Rejected {studentnum}'s ballot: incomplete")
        return False


candidates = get_candidates(CANDIDACY_FILE,
                            joint_candidates=joints, nts=names_to_change)

joint_candidates = filter(lambda x: x.joint, candidates.values())
for fill_in in fill_ins:
    candidates.update({fill_in.name: fill_in})

if USE_RAW_VOTING_INFO:
    shifted_pos_columns = [
        [n[0], int(n[1]) + RAW_VOTING_OFFSET] for n in pos_columns]
    ballots = get_ballots(BALLOT_FILE, shifted_pos_columns,
                          candidates)
else:
    ballots = get_ballots(BALLOT_FILE, pos_columns,
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


def find_corresponding_joints(candidate, joints):
    matches = []
    for j in joints:
        if candidate in j.joint_candidates:
            matches.append(j)
    return matches


all_elections = copy(elections)
complete = False
iteration = 1
final_winners = []
filter_priority = 1
problems = []
while not filter_priority > 3:
    no_new_winners = False
    while not (no_new_winners or filter_priority > 3):
        print(
            f"Running all elections... (iteration {iteration}, ranking threshold {filter_priority})")
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

            for winner, ranking in result:  # add them to cycle winners
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
            if filter_priority in rankings or (len(won_elecs) == 1 or len(won_elecs[0].candidates) == 1):
                if len(candidate.part_of_joints) > 0:
                    print("JOINTAX:", candidate)
                    # if the joint candidate won something, give them that instead (prioritize not breaking joints)
                    joints = candidate.part_of_joints
                    won_anything = False
                    for j in joints:
                        if j in cycle_winners.keys():
                            won_anything = True
                    if won_anything:
                        continue
                if len(won_elecs) == 1:  # if they only won one election, they get that role
                    won_election = won_elecs[0]
                    print(
                        f"\n (FORCED) {candidate.name} only won {won_election.position} as their #{rankings[0]} choice (final)...")

                elif len(won_elecs[0].candidates) == 1:
                    won_election = won_elecs[0]
                    print(
                        f"\n {candidate.name} won {won_election.position} as their #{rankings[0]} choice (final). They were the only person left...")

                elif filter_priority in rankings:
                    won_election = won_elecs[rankings.index(filter_priority)]
                    print(
                        f"\n{candidate.name} won {won_election.position} as their #{filter_priority} choice (final)...")
                won_election.final_winners.append(candidate)
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
            else:
                print(f"{candidate} was dropped")
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
            print(f"\n(More than {election.seats} seats filled due to a tie somewhere in the voting. or pyrankvote being dumb.")
            print("Fiddle with the maximum number of positions or take a look at raw vote counts)")



if len(problems) != 0:
    print("\n===ELECTION ISSUES===")

    for problem in problems:
        print(problem)

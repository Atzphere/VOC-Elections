import pyrankvote
import election_helper
from election_helper import get_candidates, get_ballots
from election_helper import PositionElection
from position_table import columns as pos_columns

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


for position in ballots.keys():
    pos_ballots = ballots[position]
    pos_candidates = candidates_by_pos[position]
    if position in elec_with_multi_seats.keys():
        seats = elec_with_multi_seats[position]
    else:
        seats = 1
    elec = PositionElection(position, pos_candidates, pos_ballots, seats)
    print("\n" + str(elec))

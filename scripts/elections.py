import pyrankvote
import election_helper
from election_helper import get_candidates, get_ballots
from election_helper import PositionElection
from position_table import columns as pos_columns

election_helper.MAX_POSITIONS = 3

joints = [(["Kevin McKay", "Meg Slot"], ["Membership Chair"], "Kevin McKay and Megan Slot"),
          (["Zac Wirth", "Allen Zhao"], ["Trips Coordinator"], "Zac Wirth and Allen Zhao")]


def is_eligible(line):
    studentnum = line[17]
    if line[6] == "TRUE":  # check to see if survey was finished
        return True
    else:
        print("Rejected {}'s ballot: incomplete".format(studentnum))
        return False


candidates = get_candidates("../data/Nominee_March 15, 2023_13.03.csv",
                            joint_candidates=joints)

ballots = get_ballots("../data/TEST VOC Exec Election 2023.csv", pos_columns,
                      candidates, is_eligible)

candidates_by_pos = {}
for c in candidates.values():
    pass
    print(c, c.positions)

'''
for position in ballots.keys():
    pos_ballots = ballots[position]
    elec = PositionElection(position,)
'''

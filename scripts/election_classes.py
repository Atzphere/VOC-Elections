'''
Each ballot (line in the csv) will have the voter's ranked choices for each
role in the following format:

"<position>_0_GROUP" i.e. president, etc. as the column,
<list of names in order of preference>

I.e. under President_0_GROUP, Fred has voted in a way that leaves this entry:
"Jared, Bob, Dylan, Bill"

Jared was their highest-voted candidate.

We first need to figure out who is running for what and build a list of nominees
that can be referenced using their names i.e. via a dictionary. Do this via the nominee form?
    Each nominee will have their name, contact info, + tagged vote counters for what positions
    they are running for - this will also have to be extracted from the nom. form.
    Desired positions will be ranked by priority.

In the voting form, we will individually run ranked choice for each position. (STV?)
Because of this, each candidate will need a different pyrankvote Candidate object for each
position election they are running in.

- Possibly have to handle inconsistencies between nominee forms and election stuff?


'''

import pyrankvote
import numpy as np
import csv
from typing import List
from functools import reduce


class Info:
    '''
    Import information about a candidate running in the election
    and their eligibility.

    ...

    Attributes
    ----------
        email : str
            The contact email of the candidate
        will_be_student : bool
            Whether or not the student will be a student throughout their term
            Determines eligibility.
        available terms : bool
            The terms the candidate will be at UBC for.
            Not explicity using this to determine eligbility because this is more
            case-by-case?
        eligible : bool
            Whether or not the candidate is eligible. Determined through the above
            and other future parameters.


    '''
    terms = [1, 2]

    def __init__(self, email, will_be_student, available_terms):
        self.email = email
        self.will_be_student = will_be_student
        self.available_terms = available_terms
        self.eligible = np.all([self.will_be_student])

    def __str__(self) -> str:
        if self.will_be_student:
            stud = ""
        else:
            stud = "not "
        if self.eligible:
            e = "eligible"
        else:
            e = "not eligible"
        aterms = [i for indx, i in enumerate(
            Info.terms) if self.available_terms[indx]]
        return ("Email: {}. Will {}be a student. Available in terms: {}, {}."
                .format(self.email, stud, aterms, e))

    def __eq__(self, other) -> bool:
        if other is None:
            return False
        if type(other) == str:
            return self.__str__() == other

        return self.__str__() == other.__str__()


class Candidate:
    """A candidate in the election."""

    def __init__(self, name: str, positions: tuple[str], info: Info,
                 joint: bool = False, joint_candidates: List["Candidate"] = []):
        self.name = name
        self.info = info
        self.joint = joint
        self.positions = positions
        if joint:
            self.joint_candidates = joint_candidates

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return "<Candidate('%s')>" % self.name

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other) -> bool:
        if other is None:
            return False
        if type(other) == str:
            return self.name == other

        return self.name == other.name


class Ballot:
    """
    A ballot (vote) where the voter has ranked all, or just some, of the candidates.
    If a voter lists one candidate multiple times, a DuplicateCandidatesError is thrown.
    """

    def __init__(self, ranked_candidates: List[Candidate]):
        self.ranked_candidates: List[Candidate] = tuple(ranked_candidates)

        if Ballot._is_duplicates(ranked_candidates):
            raise DuplicateCandidatesError

        if not Ballot._is_all_candidate_objects(ranked_candidates):
            raise TypeError(
                "Not all objects in ranked candidate list are of class Candidate or "
                "implement the same properties and methods"
            )

    def __repr__(self) -> str:
        candidate_name = ", ".join(
            [candidate.name for candidate in self.ranked_candidates]
        )
        return "<Ballot(%s)>" % candidate_name

    @staticmethod
    def _is_duplicates(ranked_candidates) -> bool:
        return len(set(ranked_candidates)) != len(ranked_candidates)

    @staticmethod
    def _is_all_candidate_objects(objects) -> bool:
        for obj in objects:
            if not Ballot._is_candidate_object(obj):
                return False

        # If all objects are Candidate-objects
        return True

    @staticmethod
    def _is_candidate_object(obj) -> bool:
        if obj.__class__ is Candidate:
            return True

        is_candidate_like = all(
            [hasattr(obj, "name"), hasattr(
                obj, "__hash__"), hasattr(obj, "__eq__")]
        )

        return is_candidate_like

    def remove_candidate(self, can: Candidate):
        self.ranked_candidates.remove(can)


class PositionElection:
    '''
    Class to represent an given position's election.
    ...

    Attributes:
    
    '''
    debug = True

    def __init__(self, position, candidates, ballots,
                 evaluator_method=pyrankvote.preferential_block_voting,
                 seats=1):
        self.position = position
        self.candidates = candidates
        self.ballots = ballots
        self.evaluator_method = evaluator_method

    def compute_winners(self):
        election_result = self.evaluator_method(self.candidates, self.ballots)
        if PositionElection.debug:
            print(election_result)
        winners = election_result.get_winners()
        print("The following people have won the position for {}:"
              .format(self.position))
        print(winners)
        # generate names and emails

    def remove_candidate(self, candidate):
        if candidate in self.candidates:
            self.candidates.remove(candidate)
            for ballot in self.ballots:
                if candidate.name in ballot.ranked_candidates:
                    ballot.ranked_candidates.remove()
            print("{} removed from {} election and ballots"
                  .format(candidate, self.position))


MAX_POSITIONS = 3


def get_candidates(fname: str,
                   joint_candidates: List[tuple[List[str], List[str], str]] = []):
    '''
    Generates a list of candidates to run the election off of.
    ...

    Arguments
    ---------
    fname
        File path of the csv to grab candidates from. Should be an up-to-date
        file of all candidates running for the election.
    joint_candidates
        List of all joint candidates running in the election.
        Each joint candidate entry is formatted as the following:
        (<list of candidate names as they appear in the csv file>,
        <list of the positions they are jointly running for>,
        <name they are running together under in the VOTING form
        (i.e. "Bob X and Fred Y", "Team Rocket")>)
    '''
    print("Generating candidate list from list of nominees...")
    with open(fname, newline='', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=',', quotechar='"',
                            quoting=csv.QUOTE_MINIMAL)
        data = list(reader)
        f.close()
    # election-relevant columns only start after column 18 and row 4.

    candidates = {}

    for line in data[3:]:
        surname, firstname = line[9:11]
        name = firstname + " " + surname
        email = line[11]
        status = line[17]
        cand_type = line[2]

        if cand_type == "Survey Preview":
            print("Discarded {}, was survey preview".format(name))
            continue

        if status == "Yes":
            status = True
        else:
            status = False

        terms = line[18].split(",")
        for ind, term in enumerate(terms):
            if term in ["Term 1", "Term 2"]:
                terms[ind] = True
            else:
                terms[ind] = False
        if line[19] == '':
            print("\nApplication for {} discarded due to no roles"
                  .format(name),
                  "(is a student: {}, email: {})"
                  .format(status, email))
            continue

        info = Info(email, status, terms)
        # limit number of positions people are running for to 3
        positions = line[19].split(",")[:MAX_POSITIONS]
        changed = False
        if name in candidates.keys():
            print("\n{} has submitted multiple applications."
                  .format(name))
            if (candidates[name].positions != positions):
                print("Different positions in new application, using these")
                print(
                    "({} -> {})".format(candidates[name].positions, positions))
                candidates[name].positions = positions
                changed = True
            if (candidates[name].info != info):
                print("Different info in new application, using this")
                print("({} -> {})".format(candidates[name].info, info))
                candidates[name].info = info
                changed = True
            if not changed:
                print("No relevant differences from previous application.")
        else:
            candidates.update(
                {name: Candidate(name, positions, info)})
        # candidates.append(
        #    Candidate(name, positions, Info(email, status, terms)))
    print("{} total candidates.".format(len(candidates)))
    print("handling known pairs of candidates:")
    print(joint_candidates)
    for joint in joint_candidates:
        candidate_names = joint[0]
        positions = joint[1]
        joint_name = joint[2]
        print("\nHandling {}"
              .format(joint_name))

        def find_cand(name):
            try:
                return candidates[name]
            except KeyError:
                print("{} not found in list of candidates (could mean they didn't apply for other positions)"
                      .format(name))
                return None

        relevant_candidates = filter(lambda x: x != None,
                                     [find_cand(i) for i in candidate_names])
        terms = np.unique(reduce(lambda x, y: x + y,
                                 [c.info.terms for c in relevant_candidates]))
        for can in relevant_candidates:
            for position in positions:
                can.positions.remove(position)
        emails = [c.info.email for c in relevant_candidates]
        joint_candidate = Candidate(
            joint_name, positions, Info(emails, True, terms))
        candidates.update({joint_name: joint_candidate})
        print("{} -> {}".format(joint_name, positions))
    print("... Candidate building done.")

    return candidates


if __name__ == "__main__":
    j = [(["Kevin McKay", "Meg Slot"], ["Membership Chair"], "Kevin McKay and Megan Slot"),
         (["Zac Wirth", "Allen Zhao"], ["Trips Coordinator"], "Zac Wirth and Allen Zhao")]
    get_candidates("../data/Nominee_March 15, 2023_13.03.csv",
                   joint_candidates=j)

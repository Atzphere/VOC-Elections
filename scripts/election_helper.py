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
from pyrankvote.models import DuplicateCandidatesError
import numpy as np
import csv
from typing import List
from functools import reduce
import copy

MAX_POSITIONS = 3  # by the constitution
# row at which to start reading data, use to bypass testing entries/headers
CANDIDATE_START_ROW = 9
VOTING_START_ROW = 3


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
        available terms : Tuple[Int, Int]
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
        if isinstance(other, str):
            return self.__str__() == other

        return self.__str__() == other.__str__()


class Candidate:
    """A candidate in the election."""

    def __init__(self, name: str, positions: tuple[str], info: Info,
                 joint: bool = False,
                 joint_candidates: List["Candidate"] = []):
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
        if isinstance(other, str):
            return self.name == other

        return self.name == other.name


class Ballot:
    """
    A ballot (vote) where the voter has ranked all, or just some, of the candidates.
    If a voter lists one candidate multiple times, a DuplicateCandidatesError is thrown.

    For a single position election. Modified code from pyrankvote.
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
    position : string
        The name of the position being ran for
    candidates : List[Candidate]
        List of candidates running in this election
    ballots : List[Ballot]
        List of voter ballots for this position
    evaluator_method : callable List[Candidate] List[Ballot] -> ElectionResults
        The pyrankvote (or other) method for evaluating this election
        Default of PFV.
    seats : int
        The number of seats available for this position (i.e. quartermaster
        typically has multiple.)
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
        print("The following {} for {}:"
              .format("people have won the positions"
                      if self.seats != 1 else
                      "person has won the position",
                      self.position))
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

    def __str__(self):
        return ("===Election for {}===\n".format(self.position)
                + "Candidates: {}\n".format([str(c) for c in self.candidates])
                + "{} Ballots".format(len(self.ballots)))


def get_ballots(fname: str, position_cols, candidates,
                eligibility_checker=None) -> dict[str, List[Ballot]]:
    '''
    Reads a provided qualtrics csv to get the master database of voter ballots
    to run the election off of.

    Returns a dictionary of positions with a list of their respective ballots
    ...

    Arguments
    ---------
    fname : str
        File path of the csv to read off of.

    position_cols : list[tuple(int, str)]
        List of election position names and their column numbers to read from.

    candidates : dict{name : Candidate}
        Reference list of candidates to build ballots with

    eligibility_checker : callable (str -> Bool)
        Optional function to check and filter voter eligiblity.
        Input is a line of the CSV corresponding to a ballot submission.
        It is highly recommended for this function to report why it
        rejects a given ballot for transparency.

    '''
    master_ballots = {}
    print("\nExtracting ballots from file: {}"
          .format(fname))
    with open(fname, newline='', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=',', quotechar='"',
                            quoting=csv.QUOTE_MINIMAL)
        data = list(reader)
        f.close()

    if eligibility_checker is not None:
        print("\nEligiblity-checking function supplied, filtering...")
        lines = list(filter(eligibility_checker, data[3:]))
        print("...Done")
    else:
        print("\n No eligiblity-checking function supplied, using raw lines.")
        lines = data[VOTING_START_ROW:]

    print("Building ballot database:")
    for line in lines:
        # for each ballot:
        # MODIFY THESE IN ORDER TO HANDLE DIFFERENT FORMATS
        # for roles, edit the file in the config folder.
        # finished = line[6]  # whether or not the submission was finished.
        # studentnum = line[17]
        # extract votes for each position
        for position, column in position_cols:
            # for each position in each ballot:
            # get ordered list of names in ranked order
            # generate a Ballot object.
            choices = line[int(column)].split(",")
            candidate_choices = []
            # print("{}'s votes for {}:\n{}"
            #      .format(studentnum, position, pos_ballot))

            if "Abstain" in choices:
                continue
            else:
                for choice in choices:
                    candidate_choices.append(candidates[choice])
            pos_ballot = Ballot(candidate_choices)
            if position not in master_ballots.keys():
                master_ballots.update({position: [pos_ballot]})
            else:
                master_ballots[position].append(pos_ballot)
    print("...Ballot extraction done.")
    return master_ballots


def get_candidates(fname: str,
                   joint_candidates: List[tuple[List[str],
                                                List[str], str]] = [],
                   nts: dict[str: str] = {}) -> dict[str: Candidate]:
    '''
    Generates a database of candidates to run the election off of.
    Filters and processes eligible and joint candidates
    Returns a dictionary of {name : Candidate}
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
    nts
        Dictionary of position names (key) to replace with (value).
        Used to handle inconsistent position naming between applicant
        and election csv files.

    '''
    print("Generating candidate list from list of nominees...")
    with open(fname, newline='', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=',', quotechar='"',
                            quoting=csv.QUOTE_MINIMAL)
        data = list(reader)
        f.close()
    # election-relevant columns only start after column 18 and row 4.

    candidates = {"Yes": Candidate("Yes", ("N/A",), Info("N/A", True, [])),
                  "No": Candidate("No", ("N/A",), Info("N/A", True, []))}

    # candidates_by_pos = {}

    for line in data[CANDIDATE_START_ROW:]:
        # MODIFY THESE TO HANDLE DIFFERENT FORMATS
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
        # for dealing with inconsistent position names between files
        for ind, position in enumerate(positions):
            if position in nts.keys():
                positions[ind] = nts[position]
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

    print("{} total candidates.".format(len(candidates)))
    print("Handling known pairs of candidates:")
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
        relevant_candidates = list(filter(lambda x: x is not None,
                                          list([find_cand(i) for i in candidate_names])))
        terms = np.unique(reduce(lambda x, y: x + y,
                                 [c.info.terms for c in relevant_candidates]))
        for can in relevant_candidates:
            for position in positions:
                can.positions.remove(position)
        emails = [c.info.email for c in relevant_candidates]
        joint_candidate = Candidate(
            joint_name, positions, Info(emails, True, terms),
            True, relevant_candidates)
        candidates.update({joint_name: joint_candidate})
        print("{} -> {}".format(joint_name, positions))
    print("... Candidate building done.")

    return candidates

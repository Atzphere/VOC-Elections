import pyrankvote
from pyrankvote.models import DuplicateCandidatesError
import numpy as np
import csv
from typing import List, Generator, Callable
from functools import reduce
import copy

MAX_POSITIONS = 3  # by the constitution
# row at which to start reading data, use to bypass testing entries/headers


# The following are defaults, and can/will be reconfigured from the elections.py file
CANDIDATE_START_ROW = 2
VOTING_START_ROW = 3


# all of these columns need to be included or code-handwaved in the candidate CSV.
SURNAME_COL = 9
FIRSTNAME_COL = 11
EMAIL_COL = 11
STATUS_COL = 17
CAND_TYPE_COL = 2
ROLES_COL = 19
TERMS_COL = 18


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

    def __init__(self, email, will_be_student, available_terms) -> None:
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
        return (f"Email: {self.email}. Will {stud}be a student. Available in terms: {aterms}, {e}.")

    def __eq__(self, other) -> bool:
        # equality on matching status strings
        if other is None:
            return False
        if isinstance(other, str):
            return self.__str__() == other

        return self.__str__() == other.__str__()


class Candidate:
    """
    A candidate in the election. The majority of the methods in this class
    are here as a part of the pyrankvote package's requirements.

    Attributes
    ----------
        name : str
            The candidate's name. This is actually fairly important, as it is
            used to do dictionary lookups when running elections. Candidate
            names should corroborate between nominations and ballots.
        info : Info
            Info instance for contact details, etc.
        joint : bool
            Whether or not the candidate is a joint candidate. These are
            finnicky and need their own logic. Joint candidates have to
            be filled in manually in the joint_candidates csv file. with their
        part_of_joints : List[Candidate]
            Joint candidacies the candidate is a part of.
            affiliated individual candidates.
        positions : tuple[str]
            Tuple of positions the candidate is running for. Like their name,
            this has to be consistent between nominations and ballots.

    """

    def __init__(self, name: str, positions: tuple[str], info: Info,
                 joint: bool = False, part_of_joints: List["Candidate"] = [],
                 joint_candidates: List["Candidate"] = []) -> None:
        self.name = name
        self.info = info
        self.joint = joint
        self.part_of_joints = part_of_joints
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


# Custom candidates for cases of single-candidate elections (i.e. do you approve of X?)
Yes = Candidate("Yes", ("N/A",), Info("N/A", True, []))
No = Candidate("No", ("N/A",), Info("N/A", True, []))


class Ballot:
    """
    A ballot (vote) where the voter has ranked all, or just some, of the candidates.
    If a voter lists one candidate multiple times, a DuplicateCandidatesError is thrown.

    For a single position election. Modified code from pyrankvote.

    """

    def __init__(self, ranked_candidates: List[Candidate]) -> None:
        self.ranked_candidates: List[Candidate] = ranked_candidates

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

    debug = False

    def __init__(self, position: str, candidates: List[Candidate], ballots: List[Ballot],
                 evaluator_method: Callable[[
                     List[Candidate], List[Ballot], int], pyrankvote.helpers.ElectionResults]
                 = pyrankvote.preferential_block_voting,
                 seats=1) -> None:
        self.position = position
        self.candidates = candidates
        self.starting = copy.copy(self.candidates)
        self.ballots = ballots
        self.evaluator_method = evaluator_method
        self.seats = seats
        self.final_winners = []
        self.lastwinner = None

    def compute_winners(self) -> zip:
        '''
            Compute the winners of a position election iteration.
            Results aren't necessarily final.
        '''
        if len(self.candidates) == 0:
            print("\nNo one is running for {} anymore! :("
                  .format(self.position))
            if self.lastwinner is not None:
                print("The last person to have won this position was {} with ranking {}"
                      .format(self.lastwinner.name,
                              self.lastcandidate.index(self.position) + 1))
            else:
                print("Nobody ever won {} as a preferred position."
                      .format(self.position))
                print("The original candidates were {}"
                      .format(list([c.name for c in self.starting])))
        if No in self.ballots[0].ranked_candidates or Yes in self.ballots[0].ranked_candidates:
            sole_candidate = self.candidates[0]
            tracker = 0
            for b in self.ballots:
                # if tracker ends up positive, vote passes. else no.
                if b.ranked_candidates[0].name == "Yes":
                    tracker += 1
                else:
                    tracker -= 1
            ranking = sole_candidate.positions.index(self.position) + 1
            if tracker >= 0:
                print("\n{} has won {} (only candidate in role, enough yes votes)!"
                      .format(sole_candidate.name, self.position))
                print("Their ranking for this role is #{}".format(ranking))
                self.lastwinner = sole_candidate
                result: zip[Candidate, int] = zip(
                    [self.candidates[0]], [ranking])
                return result

            if tracker < 0:  # god forbid
                print("\n{} did not win {} (only candidate in role, not enough yes votes)."
                      .format(sole_candidate.name, self.position))
                print("Their ranking for this role is #{}".format(ranking))
                return None

        elif len(self.candidates) != 0:
            election_result = self.evaluator_method(self.candidates,
                                                    self.ballots, self.seats)
            if PositionElection.debug:
                print(election_result)
            winners = election_result.get_winners()
            rankings = list([w.positions.index(self.position) + 1
                             for w in winners])
            print("\nThe following {} for {}:"
                  .format("people have won the positions"
                          if self.seats != 1 else
                          "person has won the position",
                          self.position))
            print(["{}, who ranked it #{}".format(w, r)
                   for w, r in zip(winners, rankings)])
            return zip(winners, rankings)

        # generate names and emails

    def remove_candidate(self, candidate: Candidate) -> None:
        '''
            Removes a candidate from the election. Useful if they won
            a different role. 
        '''
        if candidate in self.candidates:
            self.candidates.remove(candidate)
            for ballot in self.ballots:
                if candidate.name in ballot.ranked_candidates:
                    ballot.ranked_candidates.remove(candidate)
            print("{} removed from {} election and ballots"
                  .format(candidate, self.position))

    def __str__(self) -> str:
        return ("===~Election for {}~===\n".format(self.position)
                + "Candidates: {}\n".format([str(c) for c in self.candidates])
                + "{} Ballots\n".format(len(self.ballots))
                + "{} seats".format(self.seats))

    def __repr__(self) -> str:
        return "<PositionElection('%s')>" % self.position


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
        lines = list(filter(eligibility_checker, data[VOTING_START_ROW:]))
        print("...Done")
    else:
        print("\nNo eligiblity-checking function supplied, using raw lines.")
        lines = data[VOTING_START_ROW:]

    print("Building ballot database:")
    for line in lines:
        # for each ballot:
        # MODIFY THESE IN ORDER TO HANDLE DIFFERENT FORMATS
        # for roles, edit the file in the config folder.
        # extract votes for each position
        for position, column in position_cols:
            # for each position in each ballot:
            # get ordered list of names in ranked order
            # generate a Ballot object.
            # choices should be a list of names voted for.
            column += -1
            choices = line[int(column)].split(",")
            candidate_choices = []
            if "Abstain" in choices or "" in choices:
                continue
            else:
                for choice in choices:
                    try:
                        candidate_choices.append(candidates[choice])
                    except KeyError:
                        print(
                            f"Invalid candidate pulled with {position} at column {column} ({choice})")
                        print(
                            "If this is a joint candidacy, double check that they're acknowledged in the list of joints in elections.py")
                        print("Ballot database construction failed, aborting...")
                        exit()
            pos_ballot = Ballot(candidate_choices)
            if position not in master_ballots.keys():
                master_ballots.update({position: [pos_ballot]})
            else:
                master_ballots[position].append(pos_ballot)
    print(f"...Ballot extraction done. {len(master_ballots)} people voted!")
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
    # dummy candidate for yes/no/abstain single-candidate elections...
    candidates = {"Yes": Yes, "No": No}
    for line in data[CANDIDATE_START_ROW:]:
        # MODIFY THESE TO HANDLE DIFFERENT FORMATS
        surname, firstname = line[SURNAME_COL], line[FIRSTNAME_COL]
        if firstname == "":  # fullname should be in surname in thie case
            name = surname
        else:
            name = firstname + " " + surname
        email = line[EMAIL_COL]
        status = line[STATUS_COL]  # will they be a student?
        # for validation in case the president is lazy
        cand_type = line[CAND_TYPE_COL]
        roles = line[ROLES_COL]  # what they're running for
        terms = line[TERMS_COL].split(",")  # what terms they're available for

        if cand_type == "Survey Preview":
            print(f"Discarded {name}, was survey preview")
            continue

        if status == "Yes":
            status = True
        else:
            status = False

        for ind, term in enumerate(terms):
            if term in ["Term 1", "Term 2"]:
                terms[ind] = True
            else:
                terms[ind] = False
        if roles == '':
            print(f"\nApplication for {name} discarded due to no roles",
                  f"(is a student: {status}, email: {email})")
            continue
        if not status:
            print(f"\nApplication for {name} discarded as they're not a student",
                  f"(is a student: {status}, email: {email})")
            continue

        info = Info(email, status, terms)
        # limit number of positions people are running for to 3
        positions = roles.split(",")[:MAX_POSITIONS]
        # for dealing with inconsistent position names between files
        for ind, position in enumerate(positions):
            if position in nts.keys():
                positions[ind] = nts[position]
        changed = False
        if name in candidates.keys():
            print(f"\n{name} has submitted multiple applications.")
            if (candidates[name].positions != positions):
                print("Different positions in new application, using these")
                print(f"({candidates[name].positions} -> {positions})")
                candidates[name].positions = positions
                changed = True
            if (candidates[name].info != info):
                print("Different info in new application, using this")
                print(f"({candidates[name].info} -> {info})")
                candidates[name].info = info
                changed = True
            if not changed:
                print("No relevant differences from previous application.")
        else:
            candidates.update(
                {name: Candidate(name, positions, info)})

    print(f"\n{len(candidates)} total candidates.")
    # handle joint candidates, needs some tricky logic if they run for other different things individually
    print("Handling known pairs of candidates:")
    print(joint_candidates)
    for joint in joint_candidates:
        candidate_names = joint[0]
        positions = joint[1]
        joint_name = joint[2]
        print(f"\nHandling {joint_name}")

        def find_cand(name):
            try:
                return candidates[name]
            except KeyError:
                print(
                    f"{name} not found individually in list of candidates (could mean they didn't apply for other positions)")
                return None
        relevant_candidates = list(filter(lambda x: x is not None,
                                          list([find_cand(i) for i in candidate_names])))
        if len(relevant_candidates) == 0:
            print(
                f"Skipping {joint_name} as there don't seem to be any constituent candidates in the database.")
            continue
        terms = np.unique(reduce(lambda x, y: x + y,  # treat the joint candidacy's availability as the sum of their combined availabilities
                                 [c.info.terms for c in relevant_candidates]))
        emails = [c.info.email for c in relevant_candidates]
        joint_candidate = Candidate(
            joint_name, positions, Info(emails, True, terms),
            joint=True, joint_candidates=relevant_candidates)
        for can in relevant_candidates:  # remove the joint candidacy's positions from each individual candidate
            can.part_of_joints = [joint_candidate]
            for position in positions:
                can.positions[can.positions.index(position)] = "DUMMY"
        candidates.update({joint_name: joint_candidate})
        print(f"{joint_name} -> {positions}")
    print("... Candidate building done.")

    return candidates

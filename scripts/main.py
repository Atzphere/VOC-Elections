from elections import PositionElection
import votes_parser
from candidate_builder import candidates

def get_ballots(fname, filter : list):
    print("Extracting ballots...")
    with open(fname, newline='', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=',', quotechar='"',
                            quoting=csv.QUOTE_MINIMAL)
        data = list(reader)
        f.close()
    # election-relevant columns only start after column 18 and row 4.

    candidates = []

    for line in data[3:]:
        surname, firstname = line[9:11]
        name = firstname + " " + surname
        email = line[11]
        status = line[17]

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
            print("Application for {} discarded due to no roles"
                  .format(name),
                  "(is a student: {}, email: {})"
                  .format(status, email))
            continue

        # limit number of positions people are running for to 3
        positions = line[19].split(",")[:MAX_POSITIONS]
        candidates.append(
            Candidate(name, positions, Info(email, status, terms)))
    print("{} total candidates.".format(len(candidates)))

import pandas
import requests

VOC_API_KEY = "SAMPLE_API_KEY"
API_BASE_URL = "sample_api_url.com/api/endpoint_name"

VOC_ID_INDEX = "Q2"
UBC_ID_INDEX = "Q3"
USELESS_ROWS = 2    # the first few rows of qualtrics data are dumb and bad

# ------------------------------ HELPER FUNCTIONS ------------------------------

def validate_member(voc_id, student_number):
    """
    returns: boolean indicating whether the election response is valid
        - student number must match the one recorded for that member
        - membership type must be "Regular"
    """
    member_info = api_handler(voc_id)

    if member_info["status"] != 0:
        return False
    
    else:
        return member_info["content"]["mem_type"] == 'R' and member_info["content"]["studentnumber"] == student_number

def api_handler(voc_id):
    """
    Makes the API call to API_BASE_URL using the voc_id provided
    Returns the API response in JSON format
    """
    query = API_BASE_URL + f"?id={voc_id}"
    header = {
        "AUTH": VOC_API_KEY
    }
    response = requests.get(query, headers=header)
    return response.json()

# ------------------------------------------------------------------------------

if __name__ == '__main__':
    raw_responses = pandas.read_csv("../data/qualtrics_output.csv")

    # drop useless qualtrics rows
    raw_responses = raw_responses.drop([i for i in range(USELESS_ROWS)])
    num_responses = len(raw_responses.index)
    print(f"Retrieved {num_responses} responses from election form data")

    # remove duplicate responses from the same voc_id
    mask = raw_responses.groupby(VOC_ID_INDEX)["EndDate"].max()
    latest_responses = raw_responses[raw_responses["EndDate"].isin(mask)]
    num_latest_responses = len(latest_responses.index)
    print(f"Removed {num_responses - num_latest_responses} duplicate form submission(s). Using the most recent submission for each voter.")

    # remove submissions with invalid IDs
    verified_responses = latest_responses[latest_responses.apply(lambda response: validate_member(response[VOC_ID_INDEX], response[UBC_ID_INDEX]), axis=1)]
    num_verified_responses = len(verified_responses.index)
    print(f"Removed {num_latest_responses - num_verified_responses} submission(s) with invalid IDs")

    # write the result back to a csv
    verified_responses.to_csv('../data/verified_output.csv')
    print(f"Wrote {len(verified_responses.index)} verified response(s) to 'verified_output.csv'")


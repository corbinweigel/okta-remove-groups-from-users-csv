import requests
import json
import time
import concurrent.futures
import csv

# Okta API endpoint URLs
OKTA_API_BASE_URL = "https://YOURDOMAIN.okta.com/api/v1"
OKTA_API_USERS_URL = f"{OKTA_API_BASE_URL}/users"
OKTA_API_GROUPS_URL = f"{OKTA_API_BASE_URL}/groups"
OKTA_API_USERS_GROUP_URL = f"{OKTA_API_USERS_URL}/{{user_id}}/groups"
OKTA_API_DELETE_USER_GROUP_URL = f"{OKTA_API_GROUPS_URL}/{{group_id}}/users/{{user_id}}"

# Okta API headers
OKTA_API_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": f"SSWS yourAPIkeyHere"
}

# Maximum number of threads
max_threads = int(input("Enter the maximum number of threads: "))

# Location of the CSV file
user_list = input("Where is your CSV file located?: ")

# Define the maximum wait time for rate limiting in seconds
WAIT_TIME = 30

# Function to remove the user from all groups except the Everyone group
def remove_user_from_groups(user_email):
    # Get the user's ID
    response = requests.get(f"{OKTA_API_USERS_URL}?filter=profile.email eq \"{user_email}\"", headers=OKTA_API_HEADERS)
    if response.status_code == 200:
        data = json.loads(response.text)
        if len(data) > 0:
            user_id = data[0]["id"]
            print(f"Removing {user_email} from all groups except Everyone group...")
            # Get the list of groups the user belongs to
            response = requests.get(OKTA_API_USERS_GROUP_URL.format(user_id=user_id), headers=OKTA_API_HEADERS)
            if response.status_code == 200:
                data = json.loads(response.text)
                group_ids = []
                for group in data:
                    if group["profile"]["name"] != "Everyone":
                        group_ids.append(group["id"])
                if len(group_ids) > 0:
                    # Remove the user from each group
                    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
                        futures = [executor.submit(remove_user_from_group, user_id, group_id) for group_id in group_ids]
                        for future in concurrent.futures.as_completed(futures):
                            try:
                                data = future.result()
                            except Exception as e:
                                print(f"An error occurred while removing {user_email} from a group: {e}")
                else:
                    print(f"{user_email} is not a member of any groups.")
            else:
                print(f"An error occurred while retrieving the groups for {user_email}: {response.text}")
        else:
            print(f"No user found with email address {user_email}")
    else:
        print(f"An error occurred while retrieving the user with email address {user_email}: {response.text}")


# Function to remove the user from a specific group
def remove_user_from_group(user_id, group_id):
    retry_count = 0
    while retry_count < 6:
        response = requests.delete(OKTA_API_DELETE_USER_GROUP_URL.format(user_id=user_id, group_id=group_id), headers=OKTA_API_HEADERS)
        if response.status_code == 204:
            return True
        elif response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", "30"))
            print(f"Rate limited. Retrying in {retry_after} seconds...")
            time.sleep(retry_after)
            retry_count += 1
        elif response.status_code >= 400 and response.status_code < 500:
            print(f"An error occurred while removing the user from the group: {response.text}")
            return
# Function to remove the user from a specific group
def remove_user_from_group(user_id, group_id):
    retry_count = 0
    while retry_count < 6:
        response = requests.delete(f"{OKTA_API_GROUPS_URL}/{group_id}/users/{user_id}", headers=OKTA_API_HEADERS)
        if response.status_code == 204:
            return True
        elif response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", "30"))
            print(f"Rate limited. Retrying in {retry_after} seconds...")
            time.sleep(retry_after)
            retry_count += 1
        else:
            print(f"An error occurred while removing the user from the group: {response.text}")
            return False
        # Max retry count reached, failed to remove user from group
        if retry_count == 6:
            print(f"Max retry count reached. Failed to remove user from group {group_id}.")
            return False
        # Rate limit error, retry after waiting for 30 seconds
        elif response.status_code == 429:
            print(f"Rate limit exceeded. Retrying after {WAIT_TIME} seconds...")
            retry_count += 1
            time.sleep(WAIT_TIME)
            continue
        # Other error
        else:
            print(f"Failed to remove user from group {group_id}. Error: {response.text}")
            return False
    return False

# Function to remove users from all groups
def remove_users_from_groups():
    try:
        # Read the list of users from a CSV file
        with open(f'{user_list}', 'r') as csv_file:
            csv_reader = csv.reader(csv_file)
            users = []
            for row in csv_reader:
                users.append(row[0])
        # Remove each user from all groups except the Everyone group
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = [executor.submit(remove_user_from_groups, user) for user in users]
            for future in concurrent.futures.as_completed(futures):
                try:
                    data = future.result()
                except Exception as e:
                    print(f"An error occurred while removing the user from groups: {e}")
    except Exception as e:
        print(f"An error occurred while processing the CSV file: {e}")

# Call the function to remove users from all groups
remove_users_from_groups()

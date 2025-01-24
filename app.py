import os
import sys
import tempfile
import speech_recognition as sr
from jira import JIRAError

from jira_utils import get_jira
from setup.setup_cli import setup, load_settings, get_settings

PRODUCT_OWNERS = {
    'Damien Charlemagne': None,
    'Guillaume Rager': None,
    'Anshu Sharma': None,
    'Arnaud Garnier': None,
    'Samy Bouachour': None
}

PROJECTS = {
    'Imaging on Cloud': 'IMAGLITE',
    'Profiler': 'PROFILER'
}


def get_user_id(jira_client, user_display_name):
    users = jira_client.search_users(query=user_display_name, maxResults=1)
    for user in users:
        if user.displayName.lower() == user_display_name.lower():
            return user.accountId
    return None


def confirm_input(text):
    print(f"{text}")
    while True:
        confirmation = input("Is this correct? (Y/N): ").lower()
        if confirmation == 'y':
            return text
        elif confirmation == 'n':
            return input("✏️ Oops! Please edit the text as required: ")
        else:
            print("Please enter Y or N.")


def listen(prompt):
    recognizer = sr.Recognizer()
    while True:
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
            print(prompt)
            audio = recognizer.listen(source, timeout=5)

        try:
            result = recognizer.recognize_google(audio).lower()
            confirmed_result = confirm_input(result)
            return confirmed_result
        except sr.UnknownValueError:
            print("🥺 Could not understand. Please try again.")
        except sr.RequestError:
            print("🛠️ Speech recognition service unavailable. Please type manually.")
            return input(f"{prompt} (Manual Input): ")


def choose_from_options(prompt, options):
    print(prompt)
    for key, option in enumerate(options, 1):
        print(f"{key}. {option}")

    while True:
        try:
            choice = int(input("Enter the number of your choice: "))
            if 1 <= choice <= len(options):
                return options[choice - 1]
            print("❗ Invalid choice. Please try again.")
        except ValueError:
            print("❗ Please enter a valid number.")


def get_all_project_keys(jira_client):
    try:
        projects = jira_client.projects()
        project_data = [(project.name, project.key) for project in projects]
        return sorted(project_data, key=lambda x: x[0])
    except Exception:
        return []


def save_project_keys_to_file(project_data):
    temp_file_path = os.path.join(tempfile.gettempdir(), 'jira_project_keys.txt')

    with open(temp_file_path, 'w') as f:
        f.write("CAST Jira Project Keys:\n\n")
        for name, key in project_data:
            f.write(f"{name}: {key}\n")

    return temp_file_path


def create_ticket():
    try:
        jira_client = get_jira()

        for po in PRODUCT_OWNERS:
            PRODUCT_OWNERS[po] = get_user_id(jira_client, po)

        project_options = list(PROJECTS.keys()) + ['Other']
        project = choose_from_options("\n📂 Choose Project:", project_options)

        if project in PROJECTS:
            project_key = PROJECTS[project]
            product_owner_id = PRODUCT_OWNERS[
                'Damien Charlemagne' if project == 'Imaging on Cloud' else 'Guillaume Rager'
            ]
        else:
            while True:
                project_key_input = input("\n🗝️ Enter the project key (type 'ls' to see list): ")

                if project_key_input.lower() == 'ls':
                    project_data = get_all_project_keys(jira_client)

                    if project_data:
                        file_path = save_project_keys_to_file(project_data)
                        clickable_path = f"\033]8;;file://{file_path}\033\\{file_path}\033]8;;\033\\"
                        print(f"📝 List of Project Keys saved to: {clickable_path}")
                    else:
                        print("❗ The authentication credentials are no longer valid. Please re-configure them.")
                        sys.exit(1)

                else:
                    project_key = project_key_input.upper()
                    product_owner = choose_from_options(
                        "\n👤 Select Product Owner:",
                        list(PRODUCT_OWNERS.keys())
                    )
                    product_owner_id = PRODUCT_OWNERS[product_owner]
                    break

        issue_types = ['Story', 'Technical Story', 'Bug']
        issue_type = choose_from_options("\n📚 Choose Issue Type:", issue_types).lower()

        issue_dict = {
            'project': {
                'key': project_key},
            'issuetype': {
                'name': issue_type.title()},
            'customfield_10101': {
                'accountId': product_owner_id},
        }

        if issue_type == 'bug':
            priorities = ['Minor', 'Major', 'Critical', 'Blocker']
            priority = choose_from_options("\n🐛 Choose Priority of Bug:", priorities).lower()

            issue_dict['priority'] = {
                'name': priority.capitalize()}
            issue_dict['customfield_10175'] = '-'

        summary = listen("\n🎙️ What is the summary?")
        description = listen("\n🎙️ What is the description?")

        issue_dict.update({
            'summary': summary,
            'description': description,
        })

        new_issue = jira_client.create_issue(fields=issue_dict)
        try:
            settings = get_settings()
            current_user = jira_client.search_users(query=settings.jira_username, maxResults=1)[0]
            jira_client.assign_issue(new_issue, current_user.displayName)

            ticket_url = f"{settings.jira_server}/browse/{new_issue.key}"
            print(f"\n✅ {issue_type.capitalize()} successfully created and assigned to you!: {ticket_url}")

        except Exception as assignment_error:
            print(f"\n✅ {issue_type.capitalize()} created successfully!: {settings.jira_server}/browse/{new_issue.key}")

    except JIRAError as e:
        if "You do not have permission to create issues" in str(e):
            print(
                "❗ The authentication credentials are no longer valid or you do not have sufficient project permissions.")
            sys.exit(1)
        elif "HTTP 401" in str(e):
            print("❗ Authentication failed. Please configure your credentials.")
            sys.exit(1)
        else:
            print(e)
            sys.exit(1)
    except Exception as general_error:
        print(f"❗ An unexpected error occurred: {general_error}")
        sys.exit(1)



def main():
    args = sys.argv[1:]

    if len(args) > 0 and args[0] == "setup":
        setup()
    else:
        load_settings()
        create_ticket()


if __name__ == "__main__":
    main()

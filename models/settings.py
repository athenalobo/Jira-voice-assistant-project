from typing import List


class Settings():
    def __init__(self, jira_username: str, jira_token: str, jira_server: str, project_keys: List[str]):
        self.jira_username = jira_username
        self.jira_token = jira_token
        self.jira_server = jira_server
        self.project_keys = project_keys

    def json(self):
        return {
            "jira_username": self.jira_username,
            "jira_token": self.jira_token,
            "jira_server": self.jira_server,
            "project_keys": self.project_keys,
        }

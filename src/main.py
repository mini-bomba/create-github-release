import requests.exceptions
from github import Github
from github.GithubException import GithubException, UnknownObjectException
import os
import os.path
import glob
import time
import subprocess
import secrets


def check_input(key: str) -> bool:
    """
    Checks if a given key was passed in as an input variable
    """
    return f'INPUT_{key}' in os.environ and os.environ[f'INPUT_{key}'] != ""


def get_boolean(key: str) -> bool:
    """
    Parses an environment variable as a boolean
    """
    env = os.environ[f'INPUT_{key}'].lower()
    if env == "true":
        return True
    elif env == "false":
        return False
    else:
        print(f"::error::❌ Invalid '{key.lower()}' input argument: '{os.environ['INPUT_{key}']}'")
        exit(1)


def run_command(cmd: list[str], end_group: bool = False):
    """
    Runs a given command, surrounding output with ::stop-commands::
    :param cmd: command to run
    :param end_group: whether to run "::endgroup::" before exiting
    """
    token = secrets.token_urlsafe(32)
    print(f"::debug::Running {cmd}")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out, _ = proc.communicate()
    print(f"::stop-commands::{token}")
    print(out.decode())
    if proc.returncode != 0:
        print(f"::{token}::")
        if end_group:
            print("::endgroup::")
        print(f"::error::❌ Command {cmd} returned with non-zero exit code!")
        exit(proc.returncode)
    print(f"::{token}::")


# Read inputs & put them into variables
if not check_input("TOKEN"):
    print("::error::❌ Missing required input: token")
    exit(1)
token = os.environ['INPUT_TOKEN']
if not check_input("TAG"):
    print("::error::❌ Missing required input: tag")
    exit(1)
tag_name = os.environ['INPUT_TAG']

# A workaround for the "dubious ownership" error
print('::debug::😩 Attempting a workaround for the "dubious ownership" git error')
run_command(["git", "config", "--global", "--add", "safe.directory", "/github/workspace"])

skip_tag_creation = get_boolean("SKIP_TAG_CREATION") if check_input("SKIP_TAG_CREATION") else False
target_commit = None

if not skip_tag_creation:
    if check_input("TARGET_COMMIT"):
        target_commit = os.environ['INPUT_TARGET_COMMIT']
        if target_commit == tag_name:
            print("::warning::⚠️ target_commit and tag inputs are the same - tag creation will be skipped "
                  "(set skip_tag_creation to true to silence this warning)")
            skip_tag_creation = True
            target_commit = None
        else:
            proc = subprocess.Popen(['git', 'rev-parse', target_commit], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = proc.communicate()
            if proc.returncode != 0:
                print(f"::error::❌ Failed to resolve ref '{target_commit}' (from input 'target_commit')")
                err = err.decode()
                for line in err.split("\n"):
                    print(f"::error::{line}")
                exit(proc.returncode)
            out = out.decode().strip()
            if out != target_commit:
                print(f"🔬 Resolved reference '{target_commit}' to commit '{out}'")
            target_commit = out
    else:
        target_commit = os.environ['GITHUB_SHA']
        print(f"::debug::🔬 Attempting to resolve tag '{tag_name}' to check if it points to target_commit")
        proc = subprocess.Popen(['git', 'rev-parse', tag_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = proc.communicate()
        if proc.returncode != 0:
            print(f"::debug::🔬 Tag '{tag_name}' either doesn't exist yet, or wasn't checked out")
        else:
            out = out.decode().strip()
            print(f"::debug::🔬 Resolved tag '{tag_name}' to commit '{out}'")
            if out == target_commit:
                print(f"::warning::⚠️ Tag '{tag_name}' exists and already points to target commit '{target_commit}' - "
                      "tag creation will be skipped (set skip_tag_creation to true to silence this warning)")
                skip_tag_creation = True
                target_commit = None


if not check_input("PRERELEASE"):
    prerelease = None
else:
    prerelease = get_boolean("PRERELEASE")

if not check_input("DRAFT"):
    draft = None
else:
    draft = get_boolean("DRAFT")

if not check_input("NAME"):
    name = None
else:
    name = os.environ['INPUT_NAME']

if not check_input("BODY"):
    body = None
else:
    body = os.environ['INPUT_BODY']

files = []
if check_input("FILES"):
    for file in os.environ['INPUT_FILES'].split("\n"):
        file = file.strip()
        if len(file) <= 0:
            continue
        matches = glob.glob(file, recursive=True)
        if len(matches) <= 0:
            print(f"::warning::🤔 No files matched glob '{file}'")
        else:
            print(f"::debug::📁 {len(matches)} files matched glob '{file}': '{', '.join(matches)}'")
        files += matches
    if len(files) > 0:
        pass
    elif not check_input("FAIL_ON_NO_FILES"):
        pass
    elif get_boolean("FAIL_ON_NO_FILES"):
        print("::error::❌ No file globs matched!")
        exit(1)

clear_attachments = get_boolean("CLEAR_ATTACHMENTS") if check_input("CLEAR_ATTACHMENTS") else True

# Create Github object
github = Github(base_url=os.environ['GITHUB_API_URL'],
                login_or_token=os.environ['INPUT_TOKEN'],
                user_agent="mini-bomba/create-github-release")

# Get the repo
repo = github.get_repo(os.environ['GITHUB_REPOSITORY'])

# Check current release state
print("👀 Checking current state of the release")
release = None
try:
    release = repo.get_release(tag_name)
except UnknownObjectException:
    release = None

if release is not None:
    print("👌 Release found, copying missing input data")
    name = name or release.title
    body = body or release.body
    prerelease = prerelease if prerelease is not None else release.prerelease
    draft = draft if draft is not None else release.draft
else:
    print("❗ Release does not exists (yet)")
    prerelease = prerelease if prerelease is not None else False
    draft = draft if draft is not None else False
    if name is None:
        print("::error::Input parameter 'name' must be passed if the release does not exist")
        exit(1)
    if body is None:
        print("::error::Input parameter 'body' must be passed if the release does not exist")
        exit(1)

# Create/move tag
if skip_tag_creation:
    print("⏩ Skipping tag creation")
else:
    print("::group::🏷️ Creating/Moving the tag...")
    run_command(["git", "tag", "-f", tag_name, target_commit], end_group=True)
    run_command(["git", "push", "--force", "origin", tag_name], end_group=True)
    print("::endgroup::")

print("::group::📦 Creating/Updating the release...")
if release is not None:
    if clear_attachments:
        print("🗑 Removing existing attachments...")
        for asset in release.get_assets():
            asset_name = asset.name
            asset.delete_asset()
            print(f"✅ Deleted {asset_name}")
    print("📝 Updating data...")
    release.update_release(name, body, draft, prerelease)
    if len(files) > 0:
        print("📨 Uploading new assets...")
        for file in files:
            for retry in range(1, 4):
                try:
                    release.upload_asset(file)
                    print(f"✅ Uploaded {file}")
                    break
                except (requests.exceptions.ConnectionError, GithubException) as e:
                    if isinstance(e, GithubException) and e.status != 422:
                        raise
                    if retry < 3:
                        print(f"::warning::⚠️ Got a connection error while trying to upload asset {file} "
                              f"(attempt {retry}), retrying. Error details: {type(e).__name__}: {e}")
                        time.sleep(2)
                        for asset in release.get_assets():
                            if asset.name == os.path.basename(file):
                                print(f"🗑 Deleting duplicate asset {asset.name}")
                                asset.delete_asset()
                    else:
                        print(f"::error::❌ Could not upload asset {file} due to connection errors! "
                              f"Error details: {type(e).__name__}: {e}")
                        raise
else:
    print("📝 Creating new release...")
    release = repo.create_git_release(tag_name, name, body, draft, prerelease)
    if len(files) > 0:
        print("📨 Uploading assets...")
        for file in files:
            for retry in range(1, 4):
                try:
                    release.upload_asset(file)
                    print(f"✅ Uploaded {file}")
                    break
                except (requests.exceptions.ConnectionError, GithubException) as e:
                    if isinstance(e, GithubException) and e.status != 422:
                        raise
                    if retry < 3:
                        print(f"::warning::⚠️ Got a connection error while trying to upload asset {file} "
                              f"(attempt {retry}), retrying. Error details: {type(e).__name__}: {e}")
                        time.sleep(2)
                        for asset in release.get_assets():
                            if asset.name == os.path.basename(file):
                                print(f"🗑 Deleting duplicate asset {asset.name}")
                                asset.delete_asset()
                    else:
                        print(f"::error::❌ Could not upload asset {file} due to connection errors! "
                              f"Error details: {type(e).__name__}: {e}")
                        raise
print("::endgroup::")
print("👌😎 Release created!")

import requests.exceptions
from github import Github
import os
import glob
import time
import subprocess

# Read inputs & put them into variables
if os.environ['INPUT_TOKEN'] == "":
    print("::error::❌ Missing required input: token")
    exit(1)
token = os.environ['INPUT_TOKEN']
if os.environ['INPUT_TAG'] == "":
    print("::error::❌ Missing required input: tag")
    exit(1)
tag_name = os.environ['INPUT_TAG']

if os.environ['INPUT_TARGET_COMMIT'] != "":
    target_commit = os.environ['INPUT_TARGET_COMMIT']
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
        print(f"🔬 Resolved reference '{target_commit}' to commit '{out}")
    target_commit = out
else:
    target_commit = os.environ['GITHUB_SHA']

if os.environ['INPUT_PRERELEASE'] == "":
    prerelease = None
elif os.environ['INPUT_PRERELEASE'].lower() == "true":
    prerelease = True
elif os.environ['INPUT_PRERELEASE'].lower() == "false":
    prerelease = False
else:
    print(f"::error::❌ Invalid 'prerelease' input argument: '{os.environ['INPUT_PRERELEASE']}'")
    exit(1)

if os.environ['INPUT_DRAFT'] == "":
    draft = None
elif os.environ['INPUT_DRAFT'].lower() == "true":
    draft = True
elif os.environ['INPUT_DRAFT'].lower() == "false":
    draft = False
else:
    print(f"::error::❌ Invalid 'draft' input argument: '{os.environ['INPUT_DRAFT']}'")
    exit(1)

if os.environ['INPUT_NAME'] == "":
    name = None
else:
    name = os.environ['INPUT_NAME']

if os.environ['INPUT_BODY'] == "":
    body = None
else:
    body = os.environ['INPUT_BODY']

files = []
if os.environ['INPUT_FILES'] != "":
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
    if os.environ['INPUT_FAIL_ON_NO_FILES'].lower() == "true":
        if len(files) <= 0:
            print("::error::❌ No file globs matched!")
            exit(1)
    elif os.environ['INPUT_FAIL_ON_NO_FILES'].lower() == "false":
        pass
    else:
        print(f"::error::❌ Invalid 'fail_on_no_files' input argument: '{os.environ['INPUT_PRERELEASE']}'")
        exit(1)

if os.environ['INPUT_CLEAR_ATTACHMENTS'].lower() == "true":
    clear_attachments = True
elif os.environ['INPUT_CLEAR_ATTACHMENTS'].lower() == "false":
    clear_attachments = False
else:
    print(f"::error::❌ Invalid 'clear_attachments' input argument: '{os.environ['INPUT_CLEAR_ATTACHMENTS']}'")
    exit(1)


# Create Github object
github = Github(base_url=f"{os.environ['GITHUB_API_URL']}",
                login_or_token=os.environ['INPUT_TOKEN'],
                user_agent="mini-bomba/create-github-release")

# Get the repo
repo = github.get_repo(os.environ['GITHUB_REPOSITORY'])

# Check current release state
print("👀 Checking current state of the release")
release = repo.get_release(tag_name)

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
print("::group::🏷️ Creating/Moving the tag...")
gitproc = subprocess.Popen(["git", "tag", tag_name, target_commit], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
out, _ = gitproc.communicate()
print("::stop-commands::git-output")
print(out.decode())
if gitproc.returncode != 0:
    print("::git-output::")
    print("::endgroup::")
    print(f"::error::❌ Command 'git tag {tag_name} {target_commit}' returned with non-zero exit code!")
    exit(gitproc.returncode)
gitproc = subprocess.Popen(["git", "push", "--force", "origin", tag_name], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
out, _ = gitproc.communicate()
print(out.decode())
print("::git-output::")
print("::endgroup::")
if gitproc.returncode != 0:
    print(f"::error::❌ Command 'git push --force origin {tag_name}' returned with non-zero exit code!")
    exit(gitproc.returncode)

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
                except requests.exceptions.ConnectionError as e:
                    if retry < 3:
                        print(f"::warning::⚠️ Got a connection error while trying to upload asset {file} "
                              f"(attempt {retry}), retrying. Error details: {type(e).__name__}: {e}")
                        time.sleep(2)
                        for asset in release.get_assets():
                            if asset.state == "new":
                                print(f"🗑 Deleting partially uploaded asset {asset.name}")
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
                except requests.exceptions.ConnectionError as e:
                    if retry < 3:
                        print(f"::warning::⚠️ Got a connection error while trying to upload asset {file} "
                              f"(attempt {retry}), retrying. Error details: {type(e).__name__}: {e}")
                        time.sleep(2)
                        for asset in release.get_assets():
                            if asset.state == "new":
                                print(f"🗑 Deleting partially uploaded asset {asset.name}")
                                asset.delete_asset()
                    else:
                        print(f"::error::❌ Could not upload asset {file} due to connection errors! "
                              f"Error details: {type(e).__name__}: {e}")
                        raise
print("::endgroup::")
print("👌😎 Release created!")

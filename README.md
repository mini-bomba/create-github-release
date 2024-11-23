# Create/Update Github Release
An Action for creating and/or overwriting a GitHub release

## What does this thing do?
This action can be used to automatically publish and/or update GitHub releases after 
compiling the code.

It can also be used for automatically updating a "latest" prerelease (and it was coded 
with this in mind), where your output file name may be different each commit, while only
keeping the latest set of binaries in the rolling release

It is made in python + docker... cause that's the languages I know

## How do I use this thing?

***Note: due to this being a docker action, it can only run on linux runners.***

### Input variables this action takes

| Input Name        | Description                                                                                                                                                                           |
|-------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| token             | **Required.** The token this action should use for accessing the GitHub API. Most often you'll want to set this to `${{ secrets.GITHUB_TOKEN }}`                                                                                       |
| tag               | **Required.** Name of the tag for the release.                                                                                                                                                                                         |
| name              | **Required for new releases.** The title of the release. If not set, the title will not be changed... unless the release does not exist; then it'll fail                                                                               |
| body       | **Required for new releases.** The description body of the release. If not set, the description body will not be changed... unless the release does not exist; then it'll fail                                                                   |
| prerelease        | **Optional.** Whether the release should be marked as a prerelease. Accepted values: true, false. Defaults to false for new releases, keeps the current setting for existing releases                                                  |
| draft             | **Optional.** Whether the release should be marked as a draft. Accepted values: true, false. Defaults to false for new releases, keeps the current setting for existing releases                                                       |
| target_commit     | **Optional.** Commit, branch or tag (or anything `git rev-parse` can resolve) the release tag should be created at or moved to. Defaults to `$GITHUB_SHA`, aka. the "current" commit, ignored when `skip_tag_creation` is set to true. |
| files             | **Optional.** A newline seperated list of files to attach to the release. Recursive globbing is supported (anything the python `glob.glob()` function can resolve).                                                                    |
| fail_on_no_files  | **Optional.** Should the action fail if no filename globs match? Does nothing if no files were listed. Accepted values: true, false. Default: false.                                                                                   |
| clear_attachments | **Optional.** Should we remove all existing attachments from the release before adding new ones? Accepted values: true, false. Default: false.                                                                                         |
| skip_tag_creation | **Optional.** Should the action skip tag creation? Set to true if the tag already points to the correct commit. Accepted values: true, false. Default: false.                                                                          |

### Environment variables this action uses
Only default environment variables: `$GITHUB_SHA`, `$GITHUB_API_URL` and `$GITHUB_REPOSITORY`
No user-specified environment variables are used.

### Output variables?
This action does not output any variables.

### Secrets?
Only ones you specify: the `token`

### Any examples of usage?
Here's an example workflow:

This workflow would trigger on every push to the `master` branch, compile your code, 
move the `latest` tag to the latest commit, remove all attachments from the `latest` release, update the description 
and attach newly compiled binaries. 
```yaml
name: Test the action

on:
  push:
    branches:
      - master

jobs:
  main:
    runs-on: ubuntu-20.04
    env:
    steps:
      - name: Aquire code
        if: always()
        uses: actions/checkout@v2
      - name: Put commit hash/name in env variables
        run: |
          echo "GIT_HASH=$(git rev-parse --short=8 HEAD)" >> $GITHUB_ENV
          echo "GIT_MESSAGE<<EOF" >> $GITHUB_ENV
          git log -1 --pretty=%B >> $GITHUB_ENV
          echo "EOF" >> $GITHUB_ENV
    #
    # Some steps that compile code
    # would go here
    #
      - name: Release the new binaries
        uses: mini-bomba/create-github-release@v1.1.3
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          tag: "latest"
          prerelease: true
          name: "Latest Commit, that compiles"
          body: |
            This automatic prerelease is built from commit ${{ env.GIT_HASH }} and was triggered by @${{ github.actor }}
            [Github Actions workflow run that built this prerelease](https://github.com/${{ github.repository }}/actions/runs/${{ github.run_id }})

            Commit message:
            ${{ env.GIT_MESSAGE }}
          files: |
            build/*.exe
          clear_attachments: true
```
## Using the ghcr.io image instead of building on demand
I provide automatically-built docker images via Gihub Packages, which are compatible with any workflows using the action.
If my action takes too long to build on demand for you, or if you have issues with multiple copies cluttering up your
selfhosted runner's disk space, you can use the prebuilt images instead.

To replace the action with the prebuilt image, simply replace
```yaml
uses: mini-bomba/create-github-release@v1.2.0
```
with
```yaml
uses: docker://ghcr.io/mini-bomba/create-github-release:v1.2.0
```
in your workflows.

The images are built for any version tag and any commit on the main branch.
Note that commit images are tagged with the first 7 characters of the commit hash.
The `main` tag points to the latest, non-failing commit on the main branch.
The `latest` tag points to the latest release.
See the package page for more info.

The images should work in the same way as the action, no further changes to the workflow should be required.

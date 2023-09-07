from importlib.metadata import version, PackageNotFoundError

from setuptools import setup
from os import path, getcwd
import git
import time

with open(path.join(getcwd(), 'server', 'version.py'), 'wt') as version_py:
    repo = git.Repo('/dummy_git',search_parent_directories=True)
    sha = repo.head.commit.hexsha
    short_sha = repo.git.rev_parse(sha, short=4)

    version_dict: dict[str, str] = {
        'commit': short_sha,
        'date': time.asctime(time.gmtime(repo.head.commit.committed_date)),
        'version': 'could not determine'}

    try:
        version_dict['version'] = version('swgts')
    except PackageNotFoundError:
        pass

    version_py.write(f'VERSION_INFORMATION = {str(version_dict)}')

setup(
    setup_requires=['setuptools_scm'],
    use_scm_version=False,
)

#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: Red Hat Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = """
---
module: repository
short_description: Add source repository to add custom packages
description:
    - Add source repository to add custom packages to image
author:
    - Matthew Sandoval (@matoval)
options:
    repo_name:
        description:
            - Name of the source
        type: str
        required: true
    base_url:
        description:
            - Base url of the source
        type: str
        required: false
    type:
        description:
            - Url type
        type: str
        choices: [yum-baseurl, yum-mirrorlist, yum-metalink]
        required: false
    check_ssl:
        description:
            - Check if the https certificates are valid
        type: bool
        required: false
    check_gpg:
        description:
            - Check that the gpg keys match
        type: bool
        required: false
    gpgkey_urls:
        description:
            - List of gpg key urls
        type: list
        elements: str
        required: false
    rhsm:
        description:
            - Set true if the repository source requires a subscription
        type: bool
        required: false
    state:
        description:
            - Whether to install (present) or remove (absent)
        type: str
        choices: [present, absent]
        required: true
"""

EXAMPLES = """
- name: Add source for custom packages
  infra.osbuild.repository:
    repo_name: Everything
    base_url: https://dl.fedoraproject.org/pub/epel/9/Everything/x86_64/
    type: yum-baseurl
    check_ssl: false
    check_gpg: false
    state: present
"""

import re
import time
import json

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native, to_text, to_bytes
from ansible_collections.infra.osbuild.plugins.module_utils.weldr import Weldr


def main():
    module = AnsibleModule(
        argument_spec=dict(
            repo_name=dict(type="str", required=True),
            base_url=dict(type="str", required=False),
            type=dict(type="str", required=False, choices=["yum-baseurl", "yum-mirrorlist", "yum-metalink"]),
            check_ssl=dict(type="bool", required=False),
            check_gpg=dict(type="bool", required=False),
            gpgkey_urls=dict(type="list", required=False, elements="str", no_log=True),
            rhsm=dict(type="bool", required=False),
            state=dict(type="str", required=True, choices=["present", "absent"])
        ),
        required_if=[('state', "present", ('base_url', 'type', 'check_ssl', 'check_gpg'))]
    )

    weldr = Weldr(module)

    results = {}
    has_changed = False

    repo_exists = weldr.api.get_projects_source_info_sources(module.params["repo_name"])

    if module.params["state"] == "present":

        new_source = {}
        new_source["name"] = module.params["repo_name"]
        new_source["url"] = module.params["base_url"]
        new_source["type"] = module.params["type"]
        new_source["check_ssl"] = bool(module.params["check_ssl"])
        new_source["check_gpg"] = bool(module.params["check_gpg"])

        if module.params["rhsm"]:
            new_source["rhsm"] = module.params["rhsm"]

        if module.params["gpgkey_urls"]:
            gpgkeys = []
            for url in module.params["gpgkey_urls"]:
                gpgkeys.append(url)
            new_source["gpgkey_urls"] = gpgkeys

        if len(repo_exists["errors"]) == 0:
            # weldr has not update endpoint for sources
            isDeleted = weldr.api.delete_projects_source(module.params["repo_name"])
            if not isDeleted["status"]:
                msg = isDeleted["errors"]
            else:
                results = weldr.api.post_projects_source_new(json.dumps(new_source))
                has_changed = True
                msg = "Source repository, %s, was updated." % module.params["repo_name"]

        else:
            results = weldr.api.post_projects_source_new(json.dumps(new_source))
            has_changed = True
            msg = "New source repository, %s, was added to osbuild composer" % module.params["repo_name"]

    elif module.params["state"] == "absent":

        if len(repo_exists["errors"]) != 0:
            msg = repo_exists
        else:
            results = weldr.api.delete_projects_source(module.params["repo_name"])
            msg = "Source repository, %s, was deleted from osbuild composer" % module.params["repo_name"]
            has_changed = True

    module.exit_json(ansible_module_results=results, changed=has_changed, msg=msg)


if __name__ == "__main__":
    main()

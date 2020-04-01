from ast import literal_eval
from collections.abc import Mapping, Sequence
import enum
import json
from os.path import join
import re
from typing import Any, Dict, List, Optional
from urllib.request import urlopen
from urllib.parse import quote, urlencode

from cmkclient.exception import (
    AuthenticationError,
    Error,
    MalformedResponseError,
    ResponseError,
    ResultError,
)


__version__ = '1.6.0'


class DiscoverMode(enum.Enum):
    """
    # Members
    NEW: Only discover new services
    REMOVE: Remove exceeding services
    FIXALL: Remove exceeding services and discover new services (Tabula Rasa)
    REFRESH: Start from scratch
    """
    NEW = 'new'
    REMOVE = 'remove'
    FIXALL = 'fixall'
    REFRESH = 'refresh'

class ActivateMode(enum.Enum):
    """
    # Members
    DIRTY: Update sites with changes
    ALL: Update all slave sites
    SPECIFIC: Only update specified sites
    """
    DIRTY = 'dirty'
    ALL = 'all'
    SPECIFIC = 'specific'


# pylint: disable=too-many-public-methods
class WebApi:
    """
    Abstraction for Check_Mk Web API

    # Arguments
    check_mk_url (str): URL to Check_Mk web application, multiple formats are supported
    username (str): Name of user to connect as. Make sure this is an automation user.
    secret (str): Secret for automation user. This is different from the password!

    # Examples
    ```python
    WebApi('http://checkmk.company.com/monitor/check_mk/webapi.py', 'automation', 'secret')
    ```
    ```python
    WebApi('http://checkmk.company.com/monitor/check_mk', 'automation', 'secret')
    ```
    ```python
    WebApi('http://checkmk.company.com/monitor', 'automation', 'secret')
    ```
    """

    #
    # 0. Class set up and internal tooling
    #

    def __init__(self, check_mk_url, username, secret):
        check_mk_url = check_mk_url.rstrip('/')

        if check_mk_url.endswith('/webapi.py'):
            self.web_api_base = check_mk_url
        elif check_mk_url.endswith('/check_mk'):  # ends with /$SITE_NAME/check_mk
            self.web_api_base = join(check_mk_url, 'webapi.py')
        else:  # assume it ends with /$SITE_NAME
            self.web_api_base = join(check_mk_url, 'check_mk', 'webapi.py')

        self.username = username
        self.secret = secret

    @staticmethod
    def __format_params(params):
        """
        Copy dictionary `params`, converting all keys to strings.
        Additionally:

        * Keys associated to the value ``None`` are skipped,
        * Boolean keys are converted to strings ``1`` and ``0``
          (instead of Python's ``True`` and ``False`` std string representation).
        """
        result = {}
        for key, value in params.items():
            if value is None:
                # skip all `None` values
                continue
            elif value in [True, False]:
                # represent booleans as ``1`` or ``0``
                result[key] = ('1' if value else '0')
            elif isinstance(value, Mapping):
                result[key] = WebApi.__format_params(value)
            else:
                result[key] = value
        return result

    @staticmethod
    def __build_request_data(data, request_format):
        if not data:
            return None
        else:
            data = WebApi.__format_params(data)

        if request_format == 'json':
            request_string = 'request=' + json.dumps(data)
        elif request_format == 'python':
            request_string = 'request=' + str(data)

        request_string = quote(request_string, safe="{[]}\"=, :")

        return request_string.encode()

    def __build_request_path(self, **additional_query_params):
        query_params = {
            '_username': self.username,
            '_secret': self.secret,
        }
        if additional_query_params:
            query_params.update(additional_query_params)

        query_string = urlencode(self.__format_params(query_params))

        return '?'.join([self.web_api_base, query_string])

    def make_request(self, action, query_params=None, data=None):
        """
        Make arbitrary request to Check_Mk Web API

        # Arguments
        action (str): Action request, e.g. add_host
        query_params (dict): dict of path parameters
        data (dict): dict that will be sent as request body

        # Raises
        ResponseError: Raised when the HTTP status code != 200
        MalformedResponseError: when the body of the CheckMK reply cannot be parsed
        ResultError: when CheckMK's own result code is != 0
        """
        if not query_params:
            query_params = {}
        else:
            query_params = dict(query_params)  # work on copy

        query_params.update({'action': action})

        request_format = query_params.get('request_format', 'json')

        response = urlopen(
            self.__build_request_path(**query_params),
            self.__build_request_data(data, request_format)
        )

        if response.code != 200:
            raise ResponseError(response)

        body = response.read().decode()

        if body.startswith('Authentication error:'):
            raise AuthenticationError(body)

        output_format = query_params.get('output_format', 'json')
        if output_format == 'python':
            body_dict = literal_eval(body)
        else:
            body_dict = json.loads(body)

        try:
            result_body = body_dict['result']
            result_code = body_dict['result_code']
            if result_code == 0:
                return result_body
            else:
                raise ResultError(result_code, result_body)
        except KeyError:
                raise MalformedResponseError(response)

    #
    # 1. Activating changes
    #

    def activate_changes(self,
                         mode: ActivateMode = ActivateMode.DIRTY,
                         sites: Optional[List[str]] = None,
                         allow_foreign_changes: bool = False):
        """
        Activates all changes previously done

        # Arguments
        mode (ActivateMode): see #WebApi.ActivateMode
        sites (list): List of sites to activates changes on
        allow_foreign_changes (bool): If True changes of other users will be applied as well
        """
        data = {
            'sites': sites
        }

        query_params = {
            'mode': mode.value,
            'allow_foreign_changes': allow_foreign_changes,
        }

        return self.make_request('activate_changes', query_params=query_params, data=data)

    #
    # 2. Host commands
    #

    def add_host(self,
                 hostname: str,
                 folder: str = '/',
                 ipaddress: Optional[str] = None,
                 alias: Optional[str] = None,
                 tags: Optional[Dict[str, str]] = None,
                 **custom_attrs):
        """
        Adds a nonexistent host to the Check_MK inventory

        # Arguments
        hostname (str): Name of host to add
        folder (str): Name of folder to add the host to
        ipaddress (str): IP address of host
        alias (str): Alias for host
        tags (dict): Dictionary of tags, prefix tag_ can be omitted
        custom_attrs (dict): dict that will get merged with generated attributes, mainly for compatibility reasons
        """
        data = {
            'hostname': hostname,
            'folder': folder,
            'attributes': {
                'ipaddress': ipaddress,
                'alias': alias,
            },
        } # type: Dict[str, Any]

        attributes = data['attributes'] # type: Dict[str, Optional[str]]
        attributes.update(custom_attrs)
        if tags:
            for tag, value in tags.items():
                prefix = 'tag_'
                if tag.startswith(prefix):
                    attributes[tag] = value
                else:
                    attributes[prefix + tag] = value

        return self.make_request('add_host', data=data)

    def edit_host(self,
                  hostname: str,
                  unset_attributes: Optional[List[str]] = None,
                  **custom_attrs):
        """
        Edits the properties of an existing host

        # Arguments
        hostname (str): Name of host to edit
        unset_attributes (list): List of attributes to unset
        custom_attrs (dict): dict that will get merged with generated attributes, mainly for compatibility reasons
        """
        return self.make_request('edit_host', data={
            'hostname': hostname,
            'unset_attributes': unset_attributes,
            'attributes': custom_attrs
        })

    def delete_host(self, hostname: str):
        """
        Deletes a host from the Check_MK inventory

        # Arguments
        hostname (str): Name of host to delete
        """
        return self.make_request('delete_host', data={
            'hostname': hostname
        })

    def delete_hosts(self, hostnames: List[str]):
        """
        Deletes hosts from the Check_MK inventory.

        Only available in Check_MK starting version 1.5.0.

        # Arguments
        hostnames (list): Name of host to delete
        """
        return self.make_request('delete_host', data={
            'hostnames': hostnames
        })

    def delete_all_hosts(self):
        """
        Deletes all hosts from the Check_MK inventory.

        This is an extension not present in the Check_MK API.
        """
        all_hosts = self.get_all_hosts()

        for hostname in all_hosts:
            self.delete_host(hostname)

    def get_host(self,
                 hostname: str,
                 effective_attributes: bool = False):
        """
        Gets one host

        # Arguments
        hostname (str): Name of host to get
        effective_attributes (bool): If True attributes with default values will be returned
        """
        return self.make_request(
            'get_host',
            data={'hostname': hostname},
            query_params={'effective_attributes': effective_attributes})

    def get_all_hosts(self,
                      effective_attributes: bool = False):
        """
        Gets all hosts

        # Arguments
        effective_attributes (bool): If True attributes with default values will be returned
        """
        return self.make_request(
            'get_all_hosts',
            query_params={'effective_attributes': effective_attributes})

    def get_hosts_by_folder(self,
                            folder: str,
                            effective_attributes: bool = False):
        """
        Gets hosts in folder.

        This is an extension not present in the Check_MK API.

        # Arguments
        folder (str): folder to get hosts for
        effective_attributes (bool): If True attributes with default values will be returned
        """
        hosts = {}

        for host, attr in self.get_all_hosts(effective_attributes).items():
            if attr['path'] == folder:
                hosts[host] = attr

        return hosts

    __DISCOVERY_REGEX = {
        'added': [re.compile(r'.*Added (\d+),.*')],
        'removed': [re.compile(r'.*[Rr]emoved (\d+),.*')],
        'kept': [re.compile(r'.*[Kk]ept (\d+),.*')],
        'new_count': [re.compile(r'.*New Count (\d+)$'), re.compile(r'.*(\d+) new.*')]  # output changed in 1.6 so we have to try multiple patterns
    }

    def discover_services(self,
                          hostname: str,
                          mode: DiscoverMode = DiscoverMode.NEW):
        """
        Discovers the services of a specific host

        # Arguments
        hostname (str): Name of host to discover services for
        mode (DiscoverMode): see #WebApi.DiscoverMode
        """
        result = self.make_request(
            'discover_services',
            data={'hostname': hostname},
            query_params={'mode': mode.value}
        )

        counters = {}
        for k, patterns in self.__DISCOVERY_REGEX.items():
            for pattern in patterns:
                match = pattern.match(result)
                if match:
                    counters[k] = match.group(1)

        return counters

    def discover_services_for_all_hosts(self,
                                        mode: DiscoverMode = DiscoverMode.NEW):
        """
        Discovers the services of all hosts.

        This is an extension not present in the Check_MK API.

        # Arguments
        mode (DiscoverMode): see #WebApi.DiscoverMode
        """
        for host in self.get_all_hosts():
            self.discover_services(host, mode)

    #
    # 3. Directory commands
    #

    def get_folder(self,
                   folder: str,
                   effective_attributes: bool = False):
        """
        Gets one folder

        # Arguments
        folder (str): name of folder to get
        effective_attributes (bool): If True attributes with default values will be returned
        """
        return self.make_request(
            'get_folder',
            data={'folder': folder},
            query_params={'effective_attributes': effective_attributes})

    def get_all_folders(self):
        """
        Gets all folders
        """
        return self.make_request('get_all_folders')

    def add_folder(self,
                   folder: str,
                   create_parent_folders: bool = True,
                   **attributes):
        """
        Adds a new folder

        # Arguments
        folder (str): name of folder to add
        create_parent_folders (bool): when false, all folders except the last must already exist
        attributes (dict): attributes to set for the folder, look at output from #WebApi.get_folder
        """
        return self.make_request('add_folder', data={
            'folder': folder,
            'create_parent_folders': create_parent_folders,
            'attributes': attributes if attributes else {}
        })

    def edit_folder(self, folder: str, **attributes):
        """
        Edits an existing folder

        # Arguments
        folder (str): name of folder to edit
        attributes (dict): attributes to set for the folder, look at output from #WebApi.get_folder
        """
        return self.make_request('edit_folder', data={
            'folder': folder,
            'attributes': attributes if attributes else {}
        })

    def delete_folder(self, folder: str):
        """
        Deletes an existing folder

        # Arguments
        folder (str): name of folder to delete
        """
        return self.make_request('delete_folder', data={
            'folder': folder
        })

    #
    # 4. Group commands
    #

    def get_contactgroup(self, groupname: str):
        """
        Gets one contact group

        # Arguments
        group (str): name of contact group to get
        """
        return self.get_all_contactgroups()[groupname]

    def get_all_contactgroups(self):
        """
        Gets all contact groups
        """
        return self.make_request('get_all_contactgroups')

    def add_contactgroup(self, groupname: str, alias: str):
        """
        Adds a contact group

        # Arguments
        group (str): name of group to add
        alias (str): alias for group
        """
        return self.make_request('add_contactgroup', data={
            'groupname': groupname,
            'alias': alias,
        })

    def edit_contactgroup(self, groupname: str, alias: str):
        """
        Edits a contact group

        # Arguments
        group (str): name of group to edit
        alias (str): new alias for group
        """
        return self.make_request('edit_contactgroup', data={
            'groupname': groupname,
            'alias': alias,
        })

    def delete_contactgroup(self, groupname: str):
        """
        Deletes a contact group

        # Arguments
        group (str): name of group to delete
        """
        return self.make_request('delete_contactgroup', data={
            'groupname': groupname
        })

    def delete_all_contactgroups(self):
        """
        Deletes all contact groups
        """
        for groupname in self.get_all_contactgroups():
            self.delete_contactgroup(groupname)

    def get_hostgroup(self, groupname: str):
        """
        Gets one host group

        # Arguments
        group (str): name of host group to get
        """
        return self.get_all_hostgroups()[groupname]

    def get_all_hostgroups(self):
        """
        Gets all host groups
        """
        return self.make_request('get_all_hostgroups')

    def add_hostgroup(self, groupname: str, alias: str):
        """
        Adds a host group

        # Arguments
        group (str): name of group to add
        alias (str): alias for group
        """
        return self.make_request('add_hostgroup', data={
            'groupname': groupname,
            'alias': alias,
        })

    def edit_hostgroup(self, groupname: str, alias: str):
        """
        Edits a host group

        # Arguments
        group (str): name of group to edit
        alias (str): new alias for group
        """
        return self.make_request('edit_hostgroup', data={
            'groupname': groupname,
            'alias': alias,
        })

    def delete_hostgroup(self, groupname: str):
        """
        Deletes a host group

        # Arguments
        group (str): name of group to delete
        """
        return self.make_request('delete_hostgroup', data={
            'groupname': groupname,
        })

    def delete_all_hostgroups(self):
        """
        Deletes all host groups
        """
        for groupname in self.get_all_hostgroups():
            self.delete_hostgroup(groupname)

    def get_servicegroup(self, groupname: str):
        return self.get_all_servicegroups()[groupname]

    def get_all_servicegroups(self):
        """
        Gets all service groups
        """
        return self.make_request('get_all_servicegroups')

    def add_servicegroup(self, groupname: str, alias: str):
        """
        Adds a service group

        # Arguments
        group (str): name of group to add
        alias (str): alias for group
        """
        return self.make_request('add_servicegroup', data={
            'groupname': groupname,
            'alias': alias,
        })

    def edit_servicegroup(self, groupname: str, alias: str):
        """
        Edits a service group

        # Arguments
        group (str): name of group to edit
        alias (str): new alias for group
        """
        return self.make_request('edit_servicegroup', data={
            'groupname': groupname,
            'alias': alias,
        })

    def delete_servicegroup(self, groupname: str):
        """
        Deletes a service group

        # Arguments
        group (str): name of group to delete
        """
        return self.make_request('delete_servicegroup', data={
            'groupname': groupname,
        })

    def delete_all_servicegroups(self):
        """
        Deletes all service groups
        """
        for groupname in self.get_all_servicegroups():
            self.delete_servicegroup(groupname)

    #
    # 5. User commands
    #

    def get_user(self, user_id: str):
        """
        Gets a single user

        # Arguments
        user_id (str): ID of user to get
        """
        return self.get_all_users()[user_id]

    def get_all_users(self):
        """
        Gets all users and their attributes
        """
        return self.make_request('get_all_users')

    def add_user(self,
                 user_id: str,
                 alias: str,
                 password: str,
                 **custom_attrs):
        """
        Adds a new user

        # Arguments
        user_id (str): user ID that will be used to log in
        alias (str): extended text associated to the user to create
        password (str): password that will be used to log in
        custom_attrs (dict): attributes that can be set for a user, look at output from #WebApi.get_all_users
        """
        data = {
            'users': {
                user_id: {
                    'alias': alias,
                    'password': password
                }
            }
        }

        data['users'][user_id].update(custom_attrs)

        return self.make_request('add_users', data=data)

    def add_automation_user(self,
                            user_id: str,
                            alias: str,
                            automation_secret: str,
                            **custom_attrs):
        """
        Adds a new automation user

        # Arguments
        user_id (str): user ID that will be used to log in
        alias (str): extended text associated to the user to create
        automation_secret (str): secret that will be used to log in
        custom_attrs (dict): attributes that can be set for a user, look at output from #WebApi.get_all_users
        """
        data = {
            'users': {
                user_id: {
                    'alias': alias,
                    'automation_secret': automation_secret
                }
            }
        }

        data['users'][user_id].update(custom_attrs)

        return self.make_request('add_users', data=data)

    def edit_user(self,
                  user_id: str,
                  attributes: str,
                  unset_attributes: Optional[List[str]] = None):
        """
        Edits an existing user

        # Arguments
        user_id (str): ID of user to edit
        attributes (dict): attributes to set for given host
        unset_attributes (list): list of attribute keys to unset
        """
        return self.make_request('edit_users', data={
            'users': {
                user_id: {
                    'set_attributes': attributes,
                    'unset_attributes': unset_attributes or [],
                }
            }
        })

    def delete_user(self, user_id: str):
        """
        Deletes a user

        # Arguments
        user_id (str): ID of user to delete
        """
        return self.make_request('delete_users', data={
            'users': [user_id]
        })

    #
    # 6. Rule Set commands
    #

    def get_ruleset(self, ruleset: str):
        """
        Gets one rule set

        # Arguments
        ruleset (str): name of rule set to get
        """
        return self.make_request(
            'get_ruleset',
            data={'ruleset_name': ruleset,},
            query_params={'output_format': 'python'})

    def get_rulesets_info(self):
        """
        Return title, ID, and help text of all rule sets.
        """
        return self.make_request('get_rulesets_info', query_params={'output_format': 'python'})

    def set_ruleset(self,
                    ruleset_name: str,
                    ruleset: Dict[str, str]):
        """
        Edits one rule set

        # Arguments
        ruleset_name (str): ID of rule set to edit
        ruleset (dict): config that will be set, have a look at return value of #WebApi.get_ruleset
        """
        data = {
            'ruleset_name': ruleset_name,
            'ruleset': ruleset or {}
        }

        return self.make_request('set_ruleset', data=data, query_params={'request_format': 'python'})

    #
    # 7. Host tag commands
    #

    def get_hosttags(self):
        """
        Gets all host tags
        """
        return self.make_request('get_hosttags')

    def set_hosttags(self, hosttags: Dict[str, List[str]]):
        """
        Sets host tags

        As implemented by Check_MK, it is only possible to write the whole Host Tag Settings within an API-Call
        You can use the #WebApi.get_hosttags to get the current Tags, modify them and write the dict back via set_hosttags
        To ensure that no Tags are modified in the meantime you can use the configuration_hash key.

        e.g. 'configuration_hash': u'f31ea758a59473d15f378b692110996c'

        # Arguments
        hosttags (dict) with 2 mandatory keys:  { 'aux_tags' : [], 'tag_groups' : [] }
        """
        return self.make_request('set_hosttags', data=hosttags)

    #
    # 8. Sites
    #

    def get_site(self, site_id: str):
        """
        Gets a site

        # Arguments
        site_id (str): ID of site to get
        """
        return self.make_request(
            'get_site',
            data={'site_id': site_id},
            query_params={'output_format': 'python'})

    def set_site(self, site_id: str, site_config: Dict[str, Any]):
        """
        Edits the connection to a site

        # Arguments
        site_id (str): ID of site to edit
        site_config: config that will be set, have a look at return value of #WebApi.get_site
        """
        return self.make_request(
            'set_site',
            data={
                'site_id': site_id,
                'site_config': site_config or {},
            },
            query_params={'request_format': 'python'})

    def delete_site(self, site_id: str):
        """
        Deletes a connection to a site

        # Arguments
        site_id (str): ID of site to delete the connection to
        """
        return self.make_request('delete_site', data={
            'site_id': site_id
        })

    def login_site(self, site_id: str, username: str, password: str):
        """
        Logs in to site

        # Arguments
        site_id (str): ID of site to log in to
        username (str): ID of user
        password (str): associated password (in cleartext)
        """
        return self.make_request('login_site', data={
            'site_id': site_id,
            'username': username,
            'password': password
        })

    def logout_site(self, site_id: str):
        """
        Logs out of site

        # Arguments
        site_id (str): ID of site to log out of
        """
        return self.make_request('logout_site', data={
            'site_id': site_id
        })

    #
    # 9. Agent Bakery commands
    #

    def bake_agents(self):
        """
        Bakes all agents

        Enterprise Edition only!
        """
        return self.make_request('bake_agents')

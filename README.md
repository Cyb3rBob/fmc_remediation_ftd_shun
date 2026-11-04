# fmc_remediation_ftd_shun

YouTube Video on how to Install and use this Remediation:  https://www.youtube.com/watch?v=ukrC3ITIZbM&t=88s

A custom Cisco Firewall Management Center (FMC) remediation module that connects to a Cisco Firewall Threat Defense (FTD) device over SSH and sends `shun <source_ip>` in response to a correlation policy violation.

The module bundles its Python SSH dependencies so they can be deployed with the remediation package.

## Module details

| Item | Value |
| --- | --- |
| Module identifier | `TriggerFTDShun` |
| Display name | Remediation Action Using FTD Shun |
| Module version | `1.5` |
| Entry point | `ftd_shun.py` |
| Remediation type | `block_source` — Block Source IP Address |
| Required event field | `src_ip_addr` |
| Transport | Password-authenticated SSH, TCP port 22 |

## How it works

1. A correlation rule triggers the configured remediation in FMC.
2. FMC invokes the script with the remediation name and the event's source IP address.
3. The script reads firewall connection settings from `instance.conf` in its current working directory.
4. The connector opens an interactive SSH session and waits for the FTD `>` prompt.
5. The script sends `shun <source_ip>` through `send_command_clish()`, prints the returned output, and closes the connection.

For example, an event with source IP `192.0.2.100` results in:

```text
shun 192.0.2.100
```

Only source IP blocking is enabled in `module.template`. The destination blocking definition is commented out. The remediation does not schedule automatic unblocking, select an HA peer, or call the connector's upgrade and file-transfer helpers.

## Repository structure

```text
.
├── readme.md
└── module/
    ├── module.template                  # FMC module definition and configuration fields
    ├── ftd_shun.py                      # Remediation entry point
    ├── ftd_connector.py                 # Interactive FTD SSH connector
    ├── ftd_shun_remediation_bob.tar.gz   # Existing archive; see packaging note below
    └── lib/                            # Bundled dependencies and license notices
```

## Requirements

- FMC with custom remediation module support and permission to configure remediation and correlation policies.
- An FTD device reachable from the FMC execution environment on TCP port 22.
- An FTD account that can authenticate with a password and execute the `shun` command in the CLI used by this connector.
- Python 3 in the execution environment. The script uses `#!/usr/bin/env python`, so `python` must resolve to a suitable Python 3 interpreter when executed directly.
- A Linux runtime compatible with the bundled native libraries. The bundle includes Linux shared objects, including a CPython 3.9 x86-64 CFFI backend; a Windows checkout alone is not a compatible execution environment for this bundle.

This repository does not declare a tested FMC/FTD release matrix. Validate the package in the intended appliance environment before enabling automated responses.

## Package the module

**The existing `module/ftd_shun_remediation_bob.tar.gz` is 20 bytes and lists no archive members in this checkout. Build a new package from the source files for installation.**

Run the following from the repository root on a Linux build host or compatible Linux environment. These commands create a separate package and give the staged entry point executable permissions:

```bash
mkdir -p build/ftd-shun
cp module/module.template module/ftd_shun.py module/ftd_connector.py build/ftd-shun/
cp -a module/lib build/ftd-shun/
chmod +x build/ftd-shun/ftd_shun.py
tar -czf ftd_shun_remediation.tar.gz -C build/ftd-shun module.template ftd_shun.py ftd_connector.py lib
tar -tzf ftd_shun_remediation.tar.gz
```

Confirm that `module.template`, both Python files, and `lib/` appear at the archive root, without an enclosing `module/` directory. Preserve the dependency license files in `lib/`. Do not include firewall credentials or an operational `instance.conf` in the package.

Cisco documents the archive layout and packaging requirements in the [Firepower System Remediation API Guide](https://www.cisco.com/c/en/us/td/docs/security/firepower/60/api/remediation/FireSIGHT-System-Remediation-API-Guide/WritingRemedClients.pdf).

## Install and configure in FMC

1. Open **Policies > Actions > Modules** in FMC.
2. Select the newly built `ftd_shun_remediation.tar.gz` and click **Install**.
3. Open the installed **Remediation Action Using FTD Shun** module and create an instance for the target firewall.
4. Enter the connection settings described below and save the instance.
5. Add a remediation of type **Block Source IP Address** to that instance.
6. Associate the remediation with the appropriate correlation rule response and enable the correlation policy for the intended scope.

Use separate instances for different firewall connection settings. Menu labels and policy activation steps can vary by FMC release; see Cisco's [Remediations administration guide](https://www.cisco.com/c/en/us/td/docs/security/secure-firewall/management-center/admin/770/management-center-admin-77/correlation-remediations.html).

### Instance configuration

| Field | Example | Behavior |
| --- | --- | --- |
| `firewall_ip` | `192.0.2.10` | Address used for the SSH connection. |
| `firewall_username` | `remediation_user` | FTD SSH username. |
| `firewall_password` | Your account password | Password used for SSH authentication. |
| `firewall_port` | `22` | Read from configuration, but not passed to the connector. The connection uses Paramiko's default port 22. |
| `firewall_obs` | `Branch firewall` | Descriptive field exposed by the template; not read by the entry point. |

FMC creates `instance.conf` from the saved instance settings. The script expects the four connection fields under `./config/string[@name='...']`. Protect access to this file because it contains the firewall password.

## Validate operation

Use a controlled correlation event containing a source IP address that is safe to block. Review the remediation output in FMC and independently confirm the resulting shun on the target FTD.

The script prints:

```text
Shun output:
<output returned by the FTD CLI>
```

It prints `An error occurred: <details>` for exceptions caught during the connection or command phase. Inspect the returned CLI text: the script does not parse it to determine whether the firewall accepted the command.

### Manual invocation

For a controlled test in a compatible runtime, run the entry point from the directory containing the intended `instance.conf`, supplying the absolute path to the script:

```bash
python /absolute/path/to/module/ftd_shun.py block_source 192.0.2.100
```

This sends a real shun command to the configured firewall. The first argument is read but is not used to choose an action; the second argument is appended directly to `shun `. Supply only the intended source IP address.

## Operational behavior and troubleshooting

| Observation | What to check |
| --- | --- |
| `instance.conf` is missing or XML parsing fails | Confirm the execution working directory and the FMC-generated instance configuration. XML parsing occurs before the connection error handler. |
| Connection fails or authentication is rejected | Check reachability from FMC to FTD on TCP 22, SSH access settings, and the configured credentials. |
| A different SSH port was entered but is not used | The current implementation always uses port 22. |
| The session waits for a prompt or times out | Confirm that the account reaches the expected interactive FTD `>` prompt. The connector defaults to a 15-second connection timeout and 15-second initial prompt/command waits. |
| Imports fail or native libraries cannot load | Verify the Python interpreter, Linux architecture, native ABI compatibility, and that `lib/` was included in the package. |
| FMC reports completion but the address is not blocked | Review the printed CLI response and verify the device state directly. Caught exceptions are printed without an explicit nonzero exit. |

The template defines exit status `129` as “Failed to trigger FTD shun,” but the entry point does not explicitly return that code. It also does not validate the supplied address or implement retries or automatic removal of a shun.

The connector loads system host keys and uses Paramiko's `AutoAddPolicy` for unknown hosts. Authentication disables SSH agent and local key discovery and uses the supplied password. Keep credentials out of GitHub issues, commits, and shared diagnostic output.

## Bundled dependencies

Versions below are taken from the package metadata in `module/lib/`.

| Package | Version |
| --- | --- |
| Paramiko | 2.12.0 |
| cryptography | 38.0.4 |
| bcrypt | 5.0.0 |
| PyNaCl | 1.6.2 |
| cffi | 2.0.0 |
| pycparser | 2.23 |
| six | 1.17.0 |

Both project Python files add their own directory and the bundled `lib/` directory to the Python import path. A separate `pip install` is not part of the packaged deployment workflow.

## Contributing

For issues, include the FMC and FTD versions, Python runtime details, and sanitized remediation output. Exclude passwords and operational instance configuration files. Validate proposed behavioral changes against a controlled FTD device before submitting a pull request.

## License

Original project contributions are licensed under the MIT License below. Third-party material retains its existing license and copyright notices:

- `module/ftd_connector.py` identifies Josh Bronikowski as its author, carries a 2019 Cisco copyright notice, and declares the **Cisco Sample Code License, Version 1.1**. See the notice in that file and [Cisco's license information](https://developer.cisco.com/docs/licenses).
- Packages bundled in `module/lib/` retain their respective licenses, including Paramiko's LGPL terms. Refer to the `LICENSE*` files in the package metadata directories and any additional notices within those packages.

The MIT License below does not replace these third-party terms or relicense the Cisco connector.

### MIT License

Copyright (c) 2026 FMC FTD Shun project contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

# Show IPv6 neighbor cache information in Junos

[Neigh.slax](https://github.com/jumation/neigh/blob/master/neigh.slax) is a Junos op script which improves and extends the Junos `show ipv6 neighbors` command.


## Overview

Junos `show ipv6 neighbors` command provides limited options and often displays IPv6 address and rest of the information on separate lines which makes the output difficult to `match`:

![output of "show ipv6 neighbors"](https://github.com/jumation/neigh/blob/master/screencapture_show_ipv6_neighbors.gif)

[Neigh.slax](https://github.com/jumation/neigh/blob/master/neigh.slax) makes sure, that information associated with IPv6 address is on the same line:

![output of "op neigh"](https://github.com/jumation/neigh/blob/master/screencapture_op_neigh.gif)

As seen above, additional column `Interface Description` is shown. Also, `neigh` allows to search by the interface:

![output of "op neigh interface"](https://github.com/jumation/neigh/blob/master/screencapture_op_neigh_int.gif)

..by MAC address using different notations:

![output of "op neigh mac"](https://github.com/jumation/neigh/blob/master/screencapture_op_neigh_mac.gif)

..and by IPv6 address:

![output of "op neigh ip"](https://github.com/jumation/neigh/blob/master/screencapture_op_neigh_ip.gif)


All those options can be combined. In addition, [neigh.slax](https://github.com/jumation/neigh/blob/master/neigh.slax) has a `resolve` option, which shows the name of the range of IP address space from [RIR](https://www.arin.net/knowledge/rirs.html) databases and vendor name according to MAC address OUI:

![op neigh resolve](https://github.com/jumation/neigh/blob/master/screencapture_op_neigh_resolve.gif)


## Installation

Copy(for example, using [scp](https://en.wikipedia.org/wiki/Secure_copy)) the [neigh.slax](https://github.com/jumation/neigh/blob/master/neigh.slax) to `/var/db/scripts/op/` directory and enable the script file under `[edit system scripts op]`:

```
root@vmx1> file list detail /var/db/scripts/op/neigh.slax 
-rw-r--r--  1 root  wheel      12717 Oct 27 10:44 /var/db/scripts/op/neigh.slax
total files: 1

root@vmx1> show configuration system scripts | display inheritance no-comments 
op {
    file neigh.slax {
        description "Show IPv6 neighbor cache information";
        /* verify the integrity of an op script before running the script */
        checksum sha-256 5be02ca9f8874c754e4cb4527b9b7ae894ed0eecdca5c5b1a76c475aba00bb64;
    }
    no-allow-url;
}
synchronize;

root@vmx1> 
```

In case of two routing engines, the script needs to be copied to the `/var/db/scripts/op/` directory on both routing engines. In addition, `resolve` argument requires a CGI script or [special-purpose small httpd](https://github.com/jumation/neigh/blob/master/resolver.py) in management server:

![output of "systemctl status resolver"](https://github.com/jumation/neigh/blob/master/screenshot_systemctl_status_resolver.gif)



## License

[GNU General Public License v3.0](https://github.com/jumation/neigh/blob/master/LICENSE)

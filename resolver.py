#!/usr/bin/python3 -u

# Title               : resolver.py
# Last modified date  : 28.10.2018
# Author              : jumation.com
# Description         : Resolves MAC address to manufacturer name based on
#                       IEEE OUI/IAB registries and IP address to netname
#                       based on RDAP servers.
# Options             : None
# Notes               : Instead of daemon library(PEP 3143), daemonization
#                       is provided by systemd.


import sys
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
import re
from requests import get, HTTPError, ConnectionError, Timeout, RequestException
from netaddr import EUI, NotRegisteredError, AddrFormatError
import ipaddress


have_icu = False
try:
    import icu
    have_icu = True
except ImportError:
    pass


addr = "::"
port = 8080


# Returns the name of a range of IP address space.
def rdap(ip_addr):

    try:
        ip = ipaddress.ip_address(ip_addr)
    except ValueError:
        print("%s - invalid IP address" % ip_addr)
        return ""

    if ip.is_link_local:
        return "Link-local address"
    elif ip.is_private:
        return "Private address"
    else:
        # Both RIPE WHOIS REST API search(example: curl -sL -H 'Accept:
        # application/json' 'https://rest.db.ripe.net/search?source=ripe&
        # type-filter=inet6num&flags=no-referenced&
        # query-string=2001:500:4:c000::43') and RDAP(example: curl -sL
        # 'https://rdap.db.ripe.net/ip/2001:500:4:c000::43') return standardized
        # responses, but RDAP supports bootstrapping, i.e client no longer
        # needs to know, which server to query the data from.
        url = "https://rdap.db.ripe.net/ip/"


        try:
            r = get(url + str(ip), timeout=3)
            r.raise_for_status()
        # HTTP request returned an unsuccessful status code.
        except HTTPError as http_error:
            print("HTTP error: %s" % http_error)
            return ""
        # The request timed out.
        except Timeout as timeout_error:
            print("Timeout: %s" % timeout_error)
            return ""
        # DNS failure, refused connection.
        except ConnectionError as connection_error:
            print("Connection error: %s" % connection_error)
            return ""
        except RequestException as err:
            print("Error: %s" % err)
            return ""

        r_json = r.json()
    
        # Name is an identifier assigned to the network registration by the
        # registration holder. Defined in RFC7483 5.4.
        # Substitution operation is just a safety net. RIR databases itself
        # allow to use only certain ASCII printable characters for name/netname
        # attribute value.
        try:
            netname = re.sub('[^A-Za-z0-9_-]', '', r_json['name'])
            return netname[:20]
        except KeyError:
            return "-"


# Returns vendor associated with MAC address.
# There are few occasions where OUI maps to more than one organisation. For
# example, 08:00:30. In those cases, first match is returned. In addition,
# for IAB(now replaced by MA-S) registry entries the OUI 40:D8:55 is ignored
# in netaddr 0.7.19: https://github.com/drkjam/netaddr/issues/62
# Additionally, it is important to check the IEEE registries before the U/L
# bit because there is a small number of assignments made prior to adoption
# of IEEE 802 standards which have the U/L bit set. For example 02-E6-D3.
def mac_vendor(mac_addr):

    try:
        mac = EUI(mac_addr)
    except AddrFormatError:
        return "Invalid MAC"

    try:
        if mac.is_iab():
            oui = mac.iab
        else:
            oui = mac.oui
    except NotRegisteredError:
        # Words[0] attribute returns the first octet of a MAC address
        # in decimal:
        # https://netaddr.readthedocs.io/en/latest/api.html#netaddr.EUI.words
        # Bool() returns true if bitwise AND operation is not 0.
        if bool(mac.words[0] & 0b10):
            return "LA address"
        else:
            return "unknown vendor"

    return shorten(oui.registration().org)


# Based on shorten() function of Wireshark project make-manuf.py script.
# Converts a long manufacturer name to abbreviated short name.
# Examples can be seen in the second column of the Wireshark manuf file:
# https://code.wireshark.org/review/gitweb?p=wireshark.git;a=blob_plain;f=manuf
def shorten(manuf):
    # Normalize whitespace.
    manuf = ' '.join(manuf.split())
    orig_manuf = manuf
    # Add exactly one space on each end.
    manuf = u' {} '.format(manuf)
    # Convert to consistent case.
    manuf = manuf.title()
    # Remove any punctuation.
    manuf = re.sub(u"[',.()]", ' ', manuf)
    # & isn't needed when standalone.
    manuf = manuf.replace(" & ", " ")
    # Remove any "the", "inc", "plc", etc.
    pattern = re.compile(r"""
        \W(
        the|
        incorporated|
        inc|
        plc|
        systems|
        corporation|
        corp|
        s/a|
        a/s|
        ab|
        ag|
        kg|
        gmbh|
        company|
        co|
        limited|
        ltd|
        holding|
        spa
        )(?=\ )""", re.IGNORECASE | re.VERBOSE)
    manuf = re.sub(pattern, '', manuf)

    # Remove all spaces.
    manuf = re.sub('\s+', '', manuf)

    # Truncate names to a reasonable length, say, 8 characters. If
    # the string contains UTF-8, this may be substantially more than
    # 8 bytes. It might also be less than 8 visible characters. Plain
    # Python slices Unicode strings by code point, which is better
    # than raw bytes but not as good as grapheme clusters. PyICU
    # supports grapheme clusters. https://bugs.python.org/issue30717
    trunc_len = 8

    if have_icu:
        # Truncate by grapheme clusters.
        bi_ci = icu.BreakIterator.createCharacterInstance(icu.Locale('en_US'))
        bi_ci.setText(manuf)
        bounds = list(bi_ci)
        bounds = bounds[0:8]
        trunc_len = bounds[-1]

    manuf = manuf[:trunc_len]

    if manuf.lower() == orig_manuf.lower():
        # Original manufacturer name was short and simple.
        return manuf

    return u'{}'.format(manuf)


# Class http_server will handle incoming HTTP GET requests.
class http_server(BaseHTTPRequestHandler):

    # Do not print the timestamp. Timestamp is already seen in
    # systemd journal.
    def log_message(self, format, *args):
        sys.stderr.write("%s - %s\n" %
                (self.address_string(),
                format%args))


    # Handler for GET requests.
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type','text/html')
        self.end_headers()
        m = re.match('\/\?(.+)=(.+)', self.path)
        if m is not None:
            if m.group(1) == "ip_addr":
                self.wfile.write(
                    bytes("%s" % rdap(m.group(2)), "utf-8"))
            elif m.group(1) == "mac_addr":
                self.wfile.write(
                    bytes("%s" % mac_vendor(m.group(2)), "utf-8"))


class HTTPServerV6(HTTPServer):
    address_family = socket.AF_INET6


# IPv4 connections are handled by IPv6 stack by using IPv4-mapped IPv6
# addresses.
httpd = HTTPServerV6((addr, port), http_server)
print("server starts - listens on address %s and port %s" % (addr, port))


try:
    httpd.serve_forever()
except:
    KeyboardInterrupt


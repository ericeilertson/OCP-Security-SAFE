"""
Sample code that demonstrates how to generate, sign and verify a short-form 
report.

Author: Jeremy Boone
Date:   June 5th, 2023
"""
from OcpReportLib import ShortFormReport
import traceback
import sys
import json
import hashlib


# Hardcoding these is crude, but whatever, this is just an example script to
# show how it might work in field. 
#
# To quickly get up and running, you can use these openssl commands to generate the keypair:
#   $ openssl genrsa -out testkey_rsa3k.pem 3072
#   $ openssl rsa -in testkey_rsa3k.pem -pubout -out testkey_rsa3k.pub
#   $ openssl ecparam -name secp521r1 -genkey -noout -out testkey_p521.pem
#   $ openssl ec -in testkey_p521.pem -pubout -out testkey_ecdsa_p521.pub

MY_PRIV_KEY  = "testkey_p521.pem"
MY_KEYVAULT_URL = "https://MYVAULT.vault.azure.net/"
MY_PUB_KEY   = "testkey_ecdsa_p521.pub"
#MY_SIGN_ALGO = "PS512"
MY_SIGN_ALGO = "ES512"

# XXX: Note to SRPs: You must include a 'kid' header to uniquely identify your 
# signing key. 
MY_KID = "Wile E Coyote"

###############################################################################
# Generate and sign the short-form report
###############################################################################

# Construct the short form report object
rep = ShortFormReport()


# XXX: Note to SRP: if this is a certification for a source code deliverable rather
#      than a binary deliverable, then uncomment this section and provide the file
#      input file generated as:
#            "find . -type f -exec sha512sum {} \; > file_hashes.txt"
# manifest = []
# with open("file_hashes.txt") as hashfile:
#     for line in hashfile:
#         file_hash,file_name = line.split(" ",1)
#         file_description = {}
#         file_description["file_name"] = f"{file_name}".strip()
#         file_description["file_hash"] = f"{file_hash}".strip()
#         manifest.append(file_description)

# sort list to make the diff easier later
# manifest.sort( key=lambda x: x["file_name"] )
# be as explicit about the JSON formatting as possible, so this validates later
# m_str = json.dumps( manifest, sort_keys=False, separators=(',',':')).encode('utf-8')
# compute manifest hashes
# fw_hash_sha384 = hashlib.sha384( m_str, usedforsecurity=True ).hexdigest()
# fw_hash_sha512 = hashlib.sha512( m_str, usedforsecurity=True ).hexdigest()
# XXX



# Add vendor device information
# XXX: Note to SRP: This is where you must calculate the hash of the firmware 
# image that you tested.
fw_hash_sha384 = "cd484defa77e8c3e4a8dd73926e32365ea0dbd01e4eff017f211d4629cfcd8e4890dd66ab1bded9be865cd1c849800d4"
fw_hash_sha512 = "84635baabc039a8c74aed163a8deceab8777fed32dc925a4a8dacfd478729a7b6ab1cb91d7d35b49e2bd007a80ae16f292be3ea2b9d9a88cb3cc8dff6a216988"
rep.add_device(
    "ACME Inc",         # vendor name
    "Roadrunner Trap",  # product name
    "storage",          # device category
    "release_v1_2_3",   # repo tag
    "1.2.3",            # firmware version
    # fw_hash_sha384
    fw_hash_sha384,
    # fw_hash_sha512
    fw_hash_sha512
    # manifest          # optional: comment if not using
)

# Add audit information from Security Review Provider information
rep.add_audit(
    "My Pentest Corporation",  # SRP name
    "whitebox",   # Test methodology
    "2023-06-25", # Test completion date
    "1.2",         # Report version
    1,            # The OCP SAFE scope level
    )

# Add issue details.
rep.add_issue("Memory corruption when reading record from SPI flash",
              "7.9",
              "AV:L/AC:L/PR:L/UI:N/S:C/C:L/I:H/A:L",
              "CWE-111",
              "Due to insufficient input validation in the firmware, a local"
              " attacker who tampers with a configuration structure in"
              " SPI flash, can cause stack-based memory corruption."
)

# Example of issue that has an associated CVE
rep.add_issue("Debug commands enable arbitrary memory read/write",
              "8.7",
              "AV:L/AC:L/PR:L/UI:N/S:C/C:H/I:H/A:L",
              "CWE-222",
              "The firmware exposes debug command handlers that enable host-side"
              " drivers to read and write arbitrary regions of the device's"
              " SRAM.",
              cve="CVE-2014-10000"
)

# Print the short form report to console
print( "The short-form report:" )
print( rep.get_report_as_str() ) 

# Sign the short-form report (as a JWS) and print the signed report to the console
print("\n\n")
with open(MY_PRIV_KEY, "rb") as f:
    privkey = f.read()

success = rep.sign_report( privkey, MY_SIGN_ALGO, MY_KID )
# XXX: note that sign_report_azure() could be used here instead if using the
#      Azure Key Vault for key management. In that case use the following:
#        rep.sign_report_azure( MY_KEYVAULT_URL, MY_KID )
if not success:
    print( "Error encountered while signing short-form report" )
    sys.exit(1)

print("The corresponding signed JWS:")
signed_report = rep.get_signed_report()
print( signed_report )

###############################################################################
# Verify the signature
###############################################################################

# Step 1. Read the JWS header and ensure we have the correct key for the kid.
print("\n\n")
print("Checking the signed header:")
kid = rep.get_signed_report_kid( signed_report )
if kid is None:
    print( "kid is not present in JWS header." )
    sys.exit(1)

# XXX: Note for consumers of the short-form report: This is where you must 
# lookup the correct key that corresponds to the kid.
if kid != MY_KID:
    print( "Unknown kid in JWS header." )
    sys.exit(1)
else:
    print( f"Found the correct kid='{kid}'" )

# Step 2. Read the public key
print("\n\n")
print("Verifying signature...")
with open(MY_PUB_KEY, "rb") as f:
    pubkey = f.read()

try:
    decoded = rep.verify_signed_report( signed_report, pubkey )
    # XXX: note that verify_signed_report_azure() could be used here for online
    #      validation by the SRP, but the above is more appropriate for the OCP
    #      member once the public key is published. Azure-based public keys are
    #      retreived using get_public_key_azure()).
    #      If testing online validation replace the above with the following:
    #        rep.verify_signed_report_azure( MY_KEYVAULT_URL, MY_KID, signed_report )
    print( "Success!" )
    print( "\n\n" )
    print( "Decoded report:" )
    print( decoded )
except Exception:
    print( "Error during JWS decoding:" )
    traceback.print_exc()


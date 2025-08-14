import chilkat

#  This example requires the Chilkat API to have been previously unlocked.
#  See Global Unlock Sample for sample code.

password = "secret"

crypt = chilkat.CkCrypt2()
crypt.put_HashAlgorithm("SHA-1")
crypt.put_EncodingMode("base64")

#  Generate a 16-byte random nonce
prng = chilkat.CkPrng()
bd = chilkat.CkBinData()
prng.GenRandomBd(16, bd)

#  Get the current date/time in a string with this format: 2010-06-08T07:26:50Z
dt = chilkat.CkDateTime()
dt.SetFromCurrentSystemTime()
created = dt.getAsTimestamp(False)
bd.AppendString(created, "utf-8")

#  This example wishes to calculate a password digest like this:
#  Password_Digest = Base64 ( SHA-1 ( nonce + created + SHA-1(password) ) )

#  First SHA-1 digest the password...
passwordSha1 = crypt.hashStringENC(password)
#  Append the 20 binary bytes of the SHA1 hash to bd, which already contains the nonce and created date/time.
bd.AppendEncoded(passwordSha1, "base64")

passwordDigest = crypt.hashBdENC(bd)

print("Base64 password digest = " + passwordDigest)

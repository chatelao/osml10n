print("Source:", debug.getinfo(1).source)
local scriptdir = debug.getinfo(1).source:match("@?(.*/)")
print("Scriptdir:", scriptdir)

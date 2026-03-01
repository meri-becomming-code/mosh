import converter_utils, os
f=open('imsmanifest.xml', 'w')
f.write('<manifest>\n<resource href="web_resources/test.pdf"><file href="web_resources/test.pdf"/></resource>\n</manifest>')
f.close()

converter_utils.update_manifest_resource('.', 'web_resources/test.pdf', 'web_resources/test.html')
print(open('imsmanifest.xml').read())

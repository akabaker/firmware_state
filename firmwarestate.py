#!/usr/bin/python -tt
from elementtree import ElementTree
from subprocess import Popen, PIPE
import re
import yaml

class Omreport:
        """
        Use omreport to determine if system firmware is up-to-date

        """

        def __init__(self):
                """
                Grab XML output from omreport and store it
                @param: Params are command line options for omreport

                """

                self.storage_tree = self._system_xml('storage controller')
                self.system_tree = self._system_xml('system summary')

        def _system_xml(self, report):
                """
                Use subprocess to call omreport and storage output as an element tree

                """

                try:
                        output = Popen('omreport %s -fmt xml' % (report), stdout=PIPE, shell=True).communicate()[0]
                except OSError, e:
                        print "Execution failure: %s" % (e)
                        return

                try:
                        root = ElementTree.fromstring(output)
                        tree = ElementTree.ElementTree(root)
                except ExpatError, e:
                        print "ExpatError: %s" % (e)
                        return

                return tree

class FirmwareState:

        def __init__(self):
                self.attrib = 'test'


"""
obj = HardwareInfo()

for node in obj.blah.findall('//Name'):
        print node.text
        print obj.blah.find('//FirmwareVer').text

def main(type):
        Read output of omreport storage controller -fmt xml from stdin and parse it

        pat = re.compile(r'%s' % (type), re.I)

        tree = ElementTree.parse(sys.stdin)

        for node in tree.findall('//Name'):
                if pat.search(node.text):
                        print node.text
                        print tree.find('//FirmwareVer').text

if __name__ == "__main__":
    main('perc')
"""

#!/usr/bin/env python
# translates comments in code
# google translate portions are cleaned up from
#   http://www.halotis.com/2009/09/15/google-translate-api-python-script/
# everything else written by Kyle Isom <coder@kyleisom.net>
# usage:
#   ./ctrans.py -s filename
#       will translate a single file

import getopt
import os
import re
import sys
import urllib
import simplejson
 
baseUrl = "http://ajax.googleapis.com/ajax/services/language/translate"
ext     = '.en'

scrub_bcomments  = re.compile('/\\*(.+)\\*/', re.M & re.U)
scrub_lcomments  = re.compile('//(.+)', re.U & re.M)
scrub_scomments  = re.compile('#\\s*(.+)', re.U & re.M)

source_exts     = [ 'c', 'cpp', 'cc', 'h', 'hpp', 'py', 'pl' ]

 
def getSplits(text,splitLength=4500):
    """
    Translate Api has a limit on length of text(4500 characters) that can be
    translated at once, 
    """
    
    return (text[index:index + splitLength]
            for index in xrange(0, len(text), splitLength))
 
 
def translate(text,src='', to='en'):
    """
    A Python Wrapper for Google AJAX Language API:
    
        * Uses Google Language Detection, in cases source language is not provided
        with the source text
        * Splits up text if it's longer then 4500 characters, as a limit put up
        by the API
    """
 
    params = ( {
                'langpair': '%s|%s' % (src, to),
                'v': '1.0'
            } )
    
    retText = ''
    
    for text in getSplits(text):
            params['q'] = text
            
            resp=simplejson.load(
                                urllib.urlopen('%s' % (baseUrl),
                                data = urllib.urlencode(params))
                                )
            
            try:
                    retText += resp['responseData']['translatedText']
            except:
                    retText += text
    return retText


### start kyle's code ###

## handle C-style comments

# handles /* \\w+ */ comments
def trans_block_comment(comment):
    trans = str(comment.group())
    
    trans   = trans.lstrip('/*')
    trans   = trans.rstrip('*/')
    trans   = translate(trans)
    comment = '/* %s */' % trans
    
    return comment

# handle // \w+ comments
def trans_line_comment(comment):
    trans = str(comment.group())
    
    trans   = trans.lstrip('//')
    trans   = translate(trans.strip())
    comment = '// %s' % trans
    
    return comment


## handle non-C-style comments

# handle an initial '#', like in perl or python or your mom
def trans_scripting_comment(comment):
    trans   = str(comment.group())
    
    if trans.startswith('#!'): return trans
    
    trans   = trans.lstrip('#')
    trans   = translate(trans.strip())
    comment = '# %s' % trans
    
    return comment


# scan an individual file
def scan_file(filename):
    new_filename    = filename + ext
    ucode           = ''
    
    try:
        reader  = open(filename, 'rb')                  # read old source file
        ucode   = reader.read()                         # untranslated code
        writer  = open(new_filename, 'wb')              # write translated
    except IOError, e:
        print 'error on file %s, skipping...' % filename
        return None
    
    if not ucode: return None

    tcode       = scrub_bcomments.sub(trans_block_comment, ucode)
    tcode       = scrub_lcomments.sub(trans_line_comment,  ucode)
    tcode       = scrub_scomments.sub(trans_scripting_comment, ucode)
    
    # old pattern-matching code
#    tcode       = re.sub('/\*(.+)\*/', trans_block_comment, ucode, 0,
#                         re.M & re.U)
#    tcode       = re.sub('//(.+)', trans_line_comment, tcode, 0, re.M & re.U)
#    tcode       = re.sub('#\\s*(.+)', trans_scripting_comment, tcode, 0,
#                         re.M & re.U)
    
    writer.write(tcode)
    
    print 'translated %s to %s...' % (filename, new_filename)

def scan_dir(dirname):
    scanner     = os.walk(dirname, topdown=True)
    
    while True:
        try:
            scan_t = scanner.next()   # scan_t: scan tuple - (dirp, dirs, files)
        except StopIteration:
            break
        else:
            scan_list   = [ file for file in scan_t[2] if is_source(file) ]
            for file in scan_list:
                scan_file(file)

def is_source(filename):
    extension   = re.sub('^.+\\.(\\w+)$', '\\1', filename)
    if extension in source_exts: return True
    
    return False

if __name__ == '__main__':
    (opts, args) = getopt.getopt(sys.argv[1:], 's:d:')
    
    for (opt, arg) in opts:
        if opt == '-s':
            scan_file(arg)
        if opt == '-d':
            scan_dir(arg)
    
    
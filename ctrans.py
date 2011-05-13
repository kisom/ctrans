#!/usr/bin/env python
# -*- coding: utf-8 -*-
# translates comments in code
# google translate portions are cleaned up from
#   http://www.halotis.com/2009/09/15/google-translate-api-python-script/
# everything else written by Kyle Isom <coder@kyleisom.net>
# usage:
#   ./ctrans.py -s filename
#       will translate a single file


import codecs
import getopt
import multiprocessing
import os
import re
import sys
import urllib
import simplejson
 
baseUrl     = "http://ajax.googleapis.com/ajax/services/language/translate"
lang        = 'en'
ext         = '.en'
num_procs   =   8                                   # number of concurrent
                                                    # processes

encodeas    = 'koi8_u'                              # input file type
decodeas    = 'utf-8'                               # output file type
cerr        = 'strict'                              # what do with codec errors

scrub_bcomments = re.compile(r'/\*([\s\S]+?)\*/', re.M & re.U)
scrub_lcomments = re.compile(r'//(.+)', re.U & re.M)
scrub_scomments = re.compile(r'#\s*(.+)', re.U & re.M)

source_exts     = { 'c-style':[ 'c', 'cpp', 'cc', 'h', 'hpp' ],
                    'script': [ 'py', 'pl', 'rb' ] }

 
def get_splits(text, splitLength = 4500):
    """
    Translate Api has a limit on length of text(4500 characters) that can be
    translated at once, 
    """
    
    return (text[index:index + splitLength]
            for index in xrange(0, len(text), splitLength))
 
 
def translate(text, src = '', to = lang):
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
    
    for text in get_splits(text):
            print 'translation requested...',
            sys.stdout.flush()
            params['q'] = text
            
            resp = simplejson.load(
                                urllib.urlopen('%s' % (baseUrl),
                                data = urllib.urlencode(params))
                                )
            
            try:
                    retText += resp['responseData']['translatedText']
            except:
                    retText += text
            print ' received!'
    return retText


### start kyle's code ###

## handle C-style comments

# handles /* \w+ */ comments
def trans_block_comment(comment):
    print '/*'
    # comment should be arrive as a re.Match object, need to grab the group
    trans = unicode(comment.group())
    trans = trans.split('\n')
    
    # translate each line and compensate for the fact that gtrans eats your
    # formatting
    trans   = [ translate(line) for line in trans ]
    trans   = [ line.replace('/ * ', '/* ') for line in trans ]
    trans   = [ line.replace(' * /', ' */') for line in trans ]
    comment = u'\n'.join(trans)
    
    # here's your stupid translation    
    return comment

# handle // \w+ comments
def trans_line_comment(comment):
    print '//'
    trans = unicode(comment.group())
    
    trans   = trans.lstrip('//')
    trans   = translate(trans.strip())
    comment = u'// %s' % trans
    
    return comment


## handle non-C-style comments

# handle an initial '#', like in perl or python or your mom
def trans_scripting_comment(comment):
    trans   = unicode(comment.group())
    
    if trans.startswith('#!'): return trans
    
    trans   = trans.lstrip('#')
    trans   = translate(trans.strip())
    comment = '# %s' % trans
    
    return comment


### processing code ###
# the following functions handle regexes, file tree walking and file I/O

# translate an individual file
def scan_file(filename):
    new_filename    = filename + ext
    
    try:
        reader  = codecs.open(filename, 'r',            # read old source file
                              encoding=encodeas, errors = 'replace')      
        ucode   = reader.read()                         # untranslated code
        writer  = codecs.open(new_filename, 'w',        # write translated
                              encoding=decodeas)
        reader.close()
    except IOError, e:                                  # abort on IO error
        print 'error on file %s, skipping...' % filename
        print '\t(error returned was %s)' % str(e)
        return None
    
    if not ucode: return None

    if   is_source(filename):
        print 'c-style'
        tcode       = scrub_bcomments.sub(trans_block_comment, ucode)
        tcode       = scrub_lcomments.sub(trans_line_comment,  tcode)
    elif is_script(filename):
        tcode       = scrub_scomments.sub(trans_scripting_comment, ucode)
    
    writer.write(tcode.decode('utf-8'))
    
    print 'translated %s to %s...' % (filename, new_filename)

# look through a directory
def scan_dir(dirname):
    scanner     = os.walk(dirname, topdown=True)
    pool        = multiprocessing.Pool(processes = num_procs)
    file_list   = []
    
    while True:
        try:
            scan_t = scanner.next()   # scan_t: scan tuple - (dirp, dirs, files)
        except StopIteration:
            break
        else:
            for f in scan_t[2]:
                file_list.append(os.path.join(scan_t[0]), f)
                
    scan_list   = [ os.path.join(scan_t[0], file) for file in file_list
                    if is_source(file) or is_script(file) ]

    pool.map(scan_file, scan_list)
        
# detect c-style comments
def is_source(filename):
    extension   = re.sub('^.+\\.(\\w+)$', '\\1', filename)
    if extension in source_exts['c-style']: return True
    
    return False

# detect script-style comments
def is_script(filename):
    extension   = re.sub('^.+\\.(\\w+)$', '\\1', filename)
    if extension in source_exts['script']: return True
    
    return False

##### start main code #####
if __name__ == '__main__':
    (opts, args) = getopt.getopt(sys.argv[1:], 's:d:l:')
    
    for (opt, arg) in opts:
        if opt == '-s':
            scan_file(arg)
        if opt == '-d':
            scan_dir(arg)
    
    
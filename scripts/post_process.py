#!/usr/bin/env python
# Author: Thang Luong <luong.m.thang@gmail.com>, 2015

"""
"""

usage = 'Post processing translations e.g., replace <unk>' 
debug = True 

### Module imports ###
import sys
import os
import argparse # option parsing
import re # regular expression
import codecs
import text
### Function declarations ###
def process_command_line():
  """
  Return a 1-tuple: (args list).
  `argv` is a list of arguments, or `None` for ``sys.argv[1:]``.
  """
  
  parser = argparse.ArgumentParser(description=usage) # add description
  # positional arguments
  parser.add_argument('src_file', metavar='src_file', type=str, help='src file') 
  parser.add_argument('tgt_file', metavar='tgt_file', type=str, help='src unk file') 
  parser.add_argument('align_file', metavar='align_file', type=str, help='input cns directory to download decoded sents') 
  parser.add_argument('dict_file', metavar='dict_file', type=str, help='dict file') 
  parser.add_argument('ref_file', metavar='ref_file', type=str, help='ref file') 
  parser.add_argument('out_file', metavar='out_file', type=str, help='output file') 

  # optional arguments
  parser.add_argument('-o', '--option', dest='opt', type=int, default=0, help='0 -- copying unk, 1 -- alignment positions, 2 -- single unk handling (default=0), 3 -- alignment positions <unk_-1>, <unk_0>, <unk_1>, etc.')
  parser.add_argument('--reverse_alignment', dest='is_reverse_alignment', action='store_true', help='reverse alignment (tgtId-srcId) instead of srcId-tgtId')
  
  args = parser.parse_args()
  return args

def check_dir(out_file):
  dir_name = out_file #os.path.dirname(out_file)

  if dir_name != '' and os.path.exists(dir_name) == False:
    sys.stderr.write('! Directory %s doesn\'t exist, creating ...\n' % dir_name)
    os.makedirs(dir_name)

def execute(cmd):
  sys.stderr.write('# Executing: %s\n' % cmd)
  os.system(cmd)

def load_dict(dict_file):
  inf = codecs.open(dict_file, 'r', 'utf-8')
  line_id = 0
  dict_map = {}
  prob_map = {}
  for line in inf:
    tokens = re.split('\s+', line.strip())
    src_word = tokens[0]
    tgt_word = tokens[1]
    prob = float(tokens[2])
    if (src_word not in dict_map) or (prob > prob_map[src_word]):
      dict_map[src_word] = tgt_word
      prob_map[src_word] = prob
    line_id += 1
    if line_id % 100000 == 0:
      sys.stderr.write(' (%d) ' % line_id)
  sys.stderr.write('  Done! Num lines = %d\n' % line_id)
  inf.close()
  return dict_map

def process_files(align_file, src_file, tgt_file, ref_file, dict_file, out_file, opt, is_reverse_alignment):
  """
  """
  src_inf = codecs.open(src_file, 'r', 'utf-8')
  tgt_inf = codecs.open(tgt_file, 'r', 'utf-8')
  align_inf = codecs.open(align_file, 'r', 'utf-8')
  is_ref = 0
  if ref_file != '':
    ref_inf = codecs.open(ref_file, 'r', 'utf-8')
    is_ref = 1

  # load dict
  dict_map = load_dict(dict_file)

  # out_file
  ouf = codecs.open(out_file, 'w', 'utf-8')

  # post process
  unk = '<unk>'
  line_id = 0
  debug = 1
  unk_count = 0
  dictionary_count = 0
  identity_count = 0
  for src_line in src_inf:
    src_line = src_line.strip()
    tgt_line = tgt_inf.readline().strip()

    # post process
    if re.search('##AT##-##AT##', tgt_line):
      #old_tgt_line = tgt_line
      tgt_line = re.sub(' ##AT##-##AT## ', '-', tgt_line)
      #print old_tgt_line, ' -> ', tgt_line
   
    src_tokens = re.split('\s+', src_line)
    tgt_tokens = re.split('\s+', tgt_line)
    if is_ref:
      ref_line = ref_inf.readline().strip()

    # get alignment
    align_line = align_inf.readline().strip()
    if is_reverse_alignment==True: # reversed alignment tgtId-srcId
      (t2s, s2t) = text.aggregate_alignments(align_line)
    else: # normal alignment srcId-tgtId
      (s2t, t2s) = text.aggregate_alignments(align_line)
     
    new_tgt_tokens = []
    debug_count = 0
    debug_str = ''
    for tgt_pos in xrange(len(tgt_tokens)):
      tgt_token = tgt_tokens[tgt_pos]
      if tgt_tokens[tgt_pos] == unk:
        unk_count = unk_count + 1
        if tgt_pos in t2s: # aligned unk
          debug_count = debug_count + 1
          src_token = src_tokens[t2s[tgt_pos][0]]
          if src_token in dict_map: # there's a word-word translation
            tgt_token = dict_map[src_token]
            dictionary_count = dictionary_count + 1
            if debug:
              debug_str = debug_str + "dict: " + src_token + " -> " + tgt_token + '\n'
          else: # identity copy
            tgt_token = src_token
            identity_count = identity_count + 1

            if debug:
              debug_str = debug_str + "iden: " + src_token + " -> " + tgt_token + '\n'

      #if tgt_token != '##AT##-##AT##':
      new_tgt_tokens.append(tgt_token)

    out_line = ' '.join(new_tgt_tokens)
    ouf.write('%s\n' % out_line)

    # debug info
    if debug_count>0 and debug == 1:
      sys.stderr.write('# example %d\nsrc: %s\ntgt: %s\nalign: %s\n%sout: %s\n' % (line_id, src_line, tgt_line, align_line, debug_str, out_line))
      if is_ref:
        sys.stderr.write('ref: %s\n' % ref_line)
      debug = 0

    line_id += 1   # concat results

  src_inf.close()
  tgt_inf.close()
  align_inf.close()
  ouf.close()
  sys.stderr.write('# num sents = %d, unk count=%d, dictionary_count=%d, identity_count=%d\n' % (line_id, unk_count, dictionary_count, identity_count))

  # evaluating 
  if is_ref:
    script_dir = os.path.dirname(sys.argv[0]) 
    sys.stderr.write('# Before post process\n')
    os.system(script_dir + '/multi-bleu.perl ' + ref_file + ' < ' + tgt_file)
    sys.stderr.write('# After post process\n')
    os.system(script_dir + '/multi-bleu.perl ' + ref_file + ' < ' + out_file)

if __name__ == '__main__':
  args = process_command_line()
  process_files(args.align_file, args.src_file, args.tgt_file, args.ref_file, args.dict_file, args.out_file, args.opt, args.is_reverse_alignment)
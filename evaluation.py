# coding=utf-8
from __future__ import print_function

import ast
import sys
import traceback

import astor

from asdl.lang.py.py_asdl_helper import asdl_ast_to_python_ast, python_ast_to_asdl_ast
from asdl.lang.py.py_utils import tokenize_code as tokenize_py_code


def decode(examples, model, args, verbose=False):
    if verbose:
        print('evaluating %d examples' % len(examples))

    was_training = model.training
    model.eval()

    decode_results = []
    count = 0
    for example in examples:
        hyps = model.parse(example.src_sent, beam_size=args.beam_size)
        decoded_hyps = []
        for hyp_id, hyp in enumerate(hyps[:10]):
            try:
                py_ast = asdl_ast_to_python_ast(hyp.tree, model.grammar)
                code = astor.to_source(py_ast).strip()
                decoded_hyps.append((hyp, code))
            except:
                if verbose:
                    print("Exception in converting tree to code:", file=sys.stdout)
                    print('-' * 60, file=sys.stdout)
                    print('example id: %d, hypothesis id: %d' % (example.idx, hyp_id), file=sys.stdout)
                    traceback.print_exc(file=sys.stdout)
                    print('-' * 60, file=sys.stdout)

        count += 1
        if verbose and count % 50 == 0:
            print('decoded %d examples...' % count, file=sys.stdout)

        decode_results.append(decoded_hyps)

    if was_training: model.train()

    return decode_results


def evaluate(examples, parser, args, verbose=False):
    cum_acc = 0.0
    decode_results = decode(examples, parser, args, verbose=verbose)
    for example, hyps in zip(examples, decode_results):
        if hyps:
            hyp, hyp_code = hyps[0]

            ref_code = example.tgt_code
            ref_py_ast = ast.parse(ref_code).body[0]
            ref_reformatted_code = astor.to_source(ref_py_ast).strip()

            ref_code_tokens = tokenize_py_code(ref_reformatted_code)
            hyp_code_tokens = tokenize_py_code(hyp_code)

            if hyp_code_tokens == ref_code_tokens:
                cum_acc += 1

    eval_result = {'accuracy': cum_acc / len(examples)}

    return eval_result
#!/usr/bin/env python3

from typing import Union
import json

from systemrdl import RDLCompiler, RDLCompileError
from systemrdl import node


def convert_field(rdlc: RDLCompiler, obj: node.FieldNode) -> dict:
    json_obj = dict()
    json_obj['type'] = 'field'
    json_obj['inst_name'] = obj.inst_name
    json_obj['lsb'] = obj.lsb
    json_obj['msb'] = obj.msb
    json_obj['reset'] = obj.get_property('reset')
    json_obj['sw_access'] = obj.get_property('sw').name
    json_obj['desc'] = obj.get_property('desc') # description
    return json_obj


def convert_reg(rdlc: RDLCompiler, obj: node.RegNode) -> dict:
    # suppress warning for arrays
    #if obj.is_array:
        # Use the RDL Compiler message system to print an error
        # fatal() raises RDLCompileError
    #    rdlc.msg.fatal(
    #        "JSON export does not support arrays",
    #        obj.inst.inst_src_ref
    #    )

    # Convert information about the register
    json_obj = dict()
    json_obj['type'] = 'reg'
    json_obj['inst_name'] = obj.inst_name

    # set obj.current_idx to avoid ValueError: Index of array element must be known to derive address
    if obj.is_array:
        obj.current_idx = [0]

    json_obj['addr_offset'] = obj.address_offset
    
    if obj.get_property('desc') != None:
        json_obj['desc'] = obj.get_property('desc') # description

    if obj.get_property('indexdesc') != None:
        json_obj['index'] = obj.get_property('indexdesc')

    if obj.is_array:
        node_iter = obj.unrolled()
        entries = 0
        for node in node_iter:
            entries += 1

        json_obj['entries'] = entries
        json_obj['entry_size'] = obj.get_property('regwidth')

    # Iterate over all the fields in this reg and convert them
    json_obj['children'] = []
    for field in obj.fields():
        json_field = convert_field(rdlc, field)
        json_obj['children'].append(json_field)

    return json_obj


def convert_addrmap_or_regfile(rdlc: RDLCompiler, obj: Union[node.AddrmapNode, node.RegfileNode]) -> dict:
    if obj.is_array:
        rdlc.msg.fatal(
            "JSON export does not support arrays",
            obj.inst.inst_src_ref
        )

    json_obj = dict()
    if isinstance(obj, node.AddrmapNode):
        json_obj['type'] = 'addrmap'
    elif isinstance(obj, node.RegfileNode):
        json_obj['type'] = 'regfile'
    else:
        raise RuntimeError

    json_obj['inst_name'] = obj.inst_name
    json_obj['addr_offset'] = obj.address_offset


    if obj.get_property('desc') != None:
        json_obj['desc'] = obj.get_property('desc') # description

    json_obj['children'] = []
    for child in obj.children():
        if isinstance(child, (node.AddrmapNode, node.RegfileNode)):
            json_child = convert_addrmap_or_regfile(rdlc, child)
        elif isinstance(child, node.RegNode):
            json_child = convert_reg(rdlc, child)

        json_obj['children'].append(json_child)

    return json_obj


def convert_to_json(rdlc: RDLCompiler, obj: node.RootNode, path: str):
    # Convert entire register model to primitive datatypes (a dict/list tree)
    json_obj = convert_addrmap_or_regfile(rdlc, obj.top)

    # Write to a JSON file
    with open(path, "w", encoding='utf-8') as f:
        json.dump(json_obj, f, indent=4)

#-------------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    # Compile and elaborate files provided from the command line
    input_files = sys.argv[1:]
    rdlc = RDLCompiler()
    try:
        for input_file in input_files:
            rdlc.compile_file(input_file)
        root = rdlc.elaborate()
    except RDLCompileError:
        sys.exit(1)

    # Dump the register model to a JSON file
    convert_to_json(rdlc, root, "out.json")

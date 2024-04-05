# from cmp.semantic import *
from typing import Callable
from semantic_errors import *
from instance_types import *
from collections import OrderedDict
from Hulk.tools.Ast import *
from abc import ABC
from Hulk.tools.Ast import *


def fix_var_def_node(var_def: VarDefNode) -> VarDefNode:
    """Fix the AST node of the VarDefNode. If the var_type is None then it set it to 'None'"""
    var_type = var_def.var_type
    if var_type is None or var_type.isspace():
        var_def.var_type = "None"
    return var_def


def fix_method_return_type(method_def: MethodNode) -> MethodNode:
    """Fix the AST node of the MethodNode. If the return_type is None then it set it to 'None'"""
    return_type = method_def.return_type
    if return_type is None or return_type.isspace():
        method_def.return_type = "None"
    return method_def


def fix_function_return_type(
    function_def: FunctionDeclarationNode,
) -> FunctionDeclarationNode:
    """Fix the AST node of the FunctionDeclarationNode. If the return_type is None then it set it to 'None'"""
    return_type = function_def.return_type
    if return_type is None or return_type.isspace():
        function_def.return_type = "None"
    return function_def


def get_variable_info_from_var_def(var_def: VarDefNode) -> VariableInfo:
    """Returns a VariableInfo from a VarDefNode"""
    fix_var_def_node(var_def)
    return VariableInfo(var_def.var_name, var_def.var_type)


def get_variable_info_from_var_assign(var_assign: AssignNode) -> VariableInfo:
    """Returns a VariableInfo from a AssignNode"""
    return get_variable_info_from_var_def(var_assign.var_definition)


class MethodInfoBase:
    def __init__(
        self,
        name: str,
        arguments: list[VariableInfo],
        return_type: str,
    ):
        self.name: str = name
        """This is the name of the method"""
        self.arguments: list[VariableInfo] = arguments
        """This is a list of VariableInfo and stores the basic information of the parameters of the method"""
        self.return_type: str = return_type
        """This is the name of the return type"""

    def __str__(self):
        params = ", ".join(str(var_info) for var_info in self.arguments)
        return f"[method] {self.name}({params}): {self.return_type.name};"

    def __eq__(self, other):
        eq: Callable[[VariableInfo, VariableInfo], bool] = lambda x, y: x.type_name == y.type_name
        if not isinstance(other, TypeMethodInfo):
            return False
        return (
            other.name == self.name
            and other.return_type == self.return_type
            and len(other.arguments) == len(self.arguments)
            and all(
                eq(element[0], element[1])
                for element in zip(other.arguments, self.arguments)
            )
        )


class TypeMethodInfo(MethodInfoBase):
    def __init__(
        self,
        name: str,
        arguments: list[VariableInfo],
        return_type: str,
        declaration_node_pointer: MethodNode,
    ):
        super().__init__(name, arguments, return_type)
        self.declaration_pointer: MethodNode = declaration_node_pointer
        """This is the pointer to the AST node where the Method is declared"""

    def clone(self) -> Self:
        """Returns a copy of this TypeMethodInfo with all of it's properties cloned"""
        return TypeMethodInfo(
            self.name,
            [var.clone() for var in self.arguments],
            self.return_type,
            self.declaration_pointer,
        )


class TypeInfo:
    def __init__(self, name: str):
        self.name = name
        """The name of the Type"""
        self.constructor_arguments: OrderedDict[str, VariableInfo] = {}
        """The dictionary of the constructor argument variables"""
        self.initialization_expression: list[ExpressionNode] = []
        self.attributes: dict[str, VariableInfo] = {}
        """The dictionary of the variables"""
        self.methods: dict[str, TypeMethodInfo] = {}
        """The dictionary of the methods"""
        self.parent: Self = None
        """The parent type info. Could be None"""

    def clone(self) -> Self:
        """Returns a copy of this TypeInfo with all of it's properties cloned"""
        # Don't use OrderedDict here, it's not necessary
        new_type = TypeInfo(self.name)
        new_type.attributes = {
            key: value.clone() for key, value in self.attributes.items()
        }
        new_type.methods = {key: value.clone() for key, value in self.methods.items()}
        new_type.parent = self.parent
        return new_type

    def create_instance(
        self,
    ) -> TypeInstance:
        """This method create a new instance of this type.
        Creating first an instance of it's parent type in case it's defined"""
        pass

    def set_parent(
        self,
        parent: Self,
    ):
        """This method update the type with a new parent."""
        self.parent = parent

    def add_constructor_argument(self, variable: VariableInfo):
        """Adds a new constructor argument to the type. If the variable is already defined it raise a SemanticError"""
        if variable.name in self.constructor_arguments:
            raise SemanticError(
                f"The variable: {variable.name} is already defined in the constructor"
            )
        self.constructor_arguments[variable.name] = variable

    def set_parent_initialization_expressions(self, expressions: list[ExpressionNode]):
        """Sets the initialization expressions of the parent type"""
        self.initialization_expression = expressions

    def get_attribute(self, name: str) -> VariableInfo:
        """Returns the attribute with this name. If not found raise a SemanticError"""
        if name in self.attributes:
            return self.attributes[name]
        raise SemanticError(
            f"The type ({self.name}) has no attribute with name ({name})"
        )

    def define_new_attribute(self, attribute: VariableInfo, clone=False):
        """Creates a new attribute in the type. If an attribute with the same name is already defined then it raise a SemanticError"""
        if attribute.name in self.attributes:
            raise SemanticError(
                f"An attribute with name '{attribute.name}' is already defined in the type '{self.name}'"
            )
        self.attributes[attribute.name] = attribute if not clone else attribute.clone()

    def define_attributes(self, attributes: list[AssignNode]):
        """Creates new attributes from the list of AssignNode.
        If an attribute with the same name is already defined then it raise a SemanticError
        """
        variables: list[VariableInfo] = []
        for attribute in attributes:
            var_definition = attribute.var_definition
            fix_var_def_node(var_def=var_definition)
            variable = VariableInfo(var_definition.var_name, var_definition.var_type)
            variables.append(variable)
        for variable in variables:
            self.define_new_attribute(variable)

    def get_method(self, name: str):
        """Returns the method with this name. If not found raise a SemanticError"""
        if name in self.methods:
            return self.methods[name]
        raise SemanticError(
            f"There is no method named '{name}' in the type '{self.name}'"
        )

    def define_method(
        self,
        method_info: TypeMethodInfo,
        clone: bool = False,
    ):
        """Define a new method in the Type. If a method with the same name is already defined then it raise a SemanticError"""
        if method_info.name in self.methods:
            raise SemanticError(
                f"I the type '{self.name}' there is already a definition for a method with name"
            )
        self.methods[method_info.name] = (
            method_info if not clone else method_info.clone()
        )

    def define_methods(self, methods: list[MethodNode]):
        """Creates new methods from the list of MethodNode.
        If a method with the same name is already defined then it raise a SemanticError
        """
        for method in methods:
            arguments: list[VariableInfo] = []
            for arg in method.arguments:
                var_definition = arg.var_definition
                fix_var_def_node(var_def=var_definition)
                variable = VariableInfo(
                    var_definition.var_name, var_definition.var_type
                )
                arguments.append(variable)
            fix_method_return_type(method_def=method)
            method_info = TypeMethodInfo(
                method.method_name, arguments, method.return_type, method
            )
            self.define_method(method_info)

    def all_attributes(self) -> list[VariableInfo]:
        """Returns a list with all the attributes in the type"""
        return list(item[1] for item in self.attributes.items())

    def all_methods(self) -> list[TypeMethodInfo]:
        return list(item[1] for item in self.methods.items())

    def conforms_to(self, other):
        """Returns True if this type conforms to the other type. False otherwise.
        The type conforms to another type if the other type is the same or if the other type is an ancestor of this type.
        """
        return (
            other.bypass()
            or self == other
            or self.parent is not None
            and self.parent.conforms_to(other)
        )

    def bypass(self):
        return False

    def __str__(self):
        output = f"type {self.name}"
        parent = "" if self.parent is None else f" : {self.parent.name}"
        output += parent
        output += " {"
        output += "\n\t" if self.attributes or self.methods else ""
        output += "\n\t".join(str(x) for x in self.attributes)
        output += "\n\t" if self.attributes else ""
        output += "\n\t".join(str(x) for x in self.methods)
        output += "\n" if self.methods else ""
        output += "}\n"
        return output

    def __repr__(self):
        return str(self)


class FunctionInfo:
    def __init__(
        self,
        name: str,
        arguments: list[VariableInfo],
        return_type: str,
        function_pointer: FunctionDeclarationNode,
    ):
        self.name: str = name
        """The name of the function"""
        self.arguments: list[VariableInfo] = arguments
        """This is the list of Variable Info that represents each parameter of the function.
        The variable info contains information like the name of the variable and the type asociated"""
        self.return_type: str = return_type
        """This is the string with the name of the type"""
        self.function_pointer: FunctionDeclarationNode = function_pointer
        """This is the pointer to the AST where the Function is declared.
        It is needed for the step of interpreting the tree"""

    def clone(self) -> Self:
        """Returns a copy of this FunctionInfo with all of it's properties cloned"""
        return FunctionInfo(
            self.name,
            [var.clone() for var in self.arguments],
            self.return_type,
            self.function_pointer,
        )

    def __str__(self):
        output = f"function {self.name}"
        output += " ("
        params = ", ".join(f"{n.id}:{n.type_name.name}" for n in self.arguments)
        output += params
        output += ") :"
        output += self.return_type.name
        return output

    def __eq__(self, other: TypeInfo):
        return (
            other.name == self.name and other.return_type == self.return_type
        )  # and \
        # other.param_types == self.param_types


class ProtocolInfo:
    def __init__(
        self,
        name: str,
    ):
        self.name = name
        """The name of the protocol"""
        self.methods: dict[str, MethodInfoBase] = {}
        """The list of method signatures that the protocol defines"""
        self.parent: Self = None
        """The protocol parent. Could be None"""

    def define_parent(self, parent: Self):
        """Define the parent protocol of this protocol"""
        self.parent = parent

    def define_method(self, method_name: str):
        """Defines a method signature in this protocol.
        If a signature was already added it raise a SemanticError"""
        pass

    def __str__(self):
        output = f"protocol {self.name}"
        parent = (
            "" if self.parent is None else " : ".join(parent for parent in self.parent)
        )
        output += ": " + parent
        output += " {"
        output += "\n\t".join(str(x) for x in self.methods)
        output += "\n" if self.methods else ""
        output += "}\n"
        return output

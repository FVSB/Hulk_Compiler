from Hulk.tools.Ast import *
from Hulk.Semantic_Check.to_replace.type_node import *
from typing import Self
from Hulk.Semantic_Check.Scopes.Base_Buildings import HulkBase
class TypeScope:

    def control_protocol_methods(self, protocols_Methods: dict[str:ProtocolMethodNode], method: MethodNode):
        name = method.id
        if name in protocols_Methods:
            protocols_Methods.pop(name)
        return protocols_Methods

    def check_global_base_functions(self, method_name: str):
        if method_name in self.global_scope.base_function:
            raise SemanticError(f'El metodo {method_name} no puede ser definido es un valor base')

    def check_global_base_const(self, attr_name: str):
        if attr_name in self.global_scope.base_const:
            raise SemanticError(f' La constante {attr_name} no puede ser tomado como un atributo')

    def start(self, type_decl: TypeDeclarationNode, inherence_methods: dict[str:MethodNode],
              protocols_Methods: dict[str:ProtocolMethodNode]):

        for method in type_decl.features:
            if isinstance(method, MethodNode):

                name = method.id
                self.check_global_base_functions(name)
                # Controlar que se haya implementado lo de los protocolos
                protocols_Methods = self.control_protocol_methods(protocols_Methods, method)

                if name in self.methods:
                    if name in inherence_methods:
                        inherence_methods.pop(name)

                        self.override_methods[name] = method
                        """Añadir como que se hizo override"""
                        self.methods[name] = method
                        continue
                    raise SemanticError(
                        f'Method with the same name ({name}) already in the context in type:{type_decl.id}.')
                else:
                    self.methods[name] = method
                    self.sintetizados_methods[name] = method

            elif isinstance(method, AssignNode):
                assing = method
                name = assing.var.id
                if name in self.assign_attr:
                    raise SemanticError(
                        f'Assing con el mismo nombre {name} ya existe en el contexto del type:{type_decl.id}')
                else:
                    # Si no esta declarada se agrega al diccionario
                    self.assign_attr[name] = assing
            else:
                raise SemanticError(f'El tipo {type(method)} no es de un metodo ni una asignacion')

        # implementar metodos de protocolos
        if len(protocols_Methods) > 0:
            raise SemanticError(f'Existen methods de protocolos sin implementar')
        # Cargar los métodos heredados que no he hecho override como mis métodos
        self.methods.update(inherence_methods)

    def __init__(self, type_decl: TypeDeclarationNode, father: Self, global_scope: HulkBase,
                 inherence_methods: dict[str:MethodNode] = {},
                 interface_methods: dict[str:ProtocolMethodNode] = {}):
        """
        Crea un nuevo scope para el nuevo type
        """

        self.global_scope = global_scope
        self.id = type_decl.id
        self.type_decl = type_decl
        self.father = father
        self.child: list[TypeScope] = []
        self.inherence_methods_: dict[str:MethodNode] = inherence_methods.copy()
        self.protocols_Methods_: dict[str:ProtocolMethodNode] = interface_methods.copy()
        self.methods: dict[str:MethodNode]={}
        """
        Todos los metodos tanto heredados como sintetizados
        """
        self.sintetizados_methods: dict[str:MethodNode] = {}
        """
        Métodos sintetizados en esta clase
        """

        self.override_methods: dict[str:MethodNode] = {}
        """
        Para conocer que métodos se hicieron override aca
        """
        self.assign_attr: dict[str, AssignNode] = {}
        """
        para guardar las variables de la clase
        """
        self.start(type_decl, inherence_methods.copy(), interface_methods.copy())

    def contains_method(self, method_name: str) -> bool:
        return method_name in self.methods

    def get_method_base_typeScope(self, method_name: str) -> Self:
        # Diccionario diferencia para saber si es heredado o no
        diff = {key: self.inherence_methods_[key] for key in
                self.inherence_methods_.keys() - self.override_methods.keys()}

        if (method_name in diff) or (method_name in self.sintetizados_methods):
            return self
        if self.father is None or isinstance(HulkGlobalScope):
            """
            Si no tengo padre y no esta aca pues no esta en toda la jerarquía
            """
            return None
        self.father.get_method_base_typeScope(method_name)

    def is_attr_hear_or_heredado(self, attri_name: str, method_name: str) -> bool:
        """
        Devuelve True si el atributo esta en este scope o esta definido en un scope padre
        donde se redefine el metodo y se declara estos o donde se define el metodo
        """
        if attri_name in self.assign_attr:
            return True
        type_herencia = self.get_method_base_typeScope(method_name)
        return type_herencia.contains_attribute(attri_name)

    def contains_attribute(self, attri_name: str) -> bool:
        """Devuelve True o False si
          el atributo esta en este scope"""

        return attri_name in self.assign_attr

    def get_new_child_scope(self, type_decl: TypeDeclarationNode):
        child = TypeScope(type_decl, self, self.global_scope, self.methods, self.inherence_methods_)
        self.child.append(child)
        return child


########################################################
#
# Global scope
########################################################


class Type_Father_Control:
    """
    Clase para conocer los types que le faltan por tener padres
    """

    def __init__(self):

        self.types_waiting_types_father: dict[str:str] = {}
        """
        Types esperando por saber si esta declarado el padre
        """
        self.type_with_type_father: dict[str:str] = {}
        """
        Types con padres type
        """
        self.type_with_waiting_child: dict[str:list[str]] = {}
        """
        Lista de que tiene como key el padre y los hijos que este espera
        """
        self.types_name: set[str] = set()

    def set_type(self, type_name):
        self.types_name.add(type_name)
        if type_name in self.type_with_waiting_child:
            lis: str = self.type_with_waiting_child[type_name]
            for type_ in lis:
                del self.types_waiting_types_father[type_]
            del self.type_with_waiting_child[type_name]

    def set_type_and_father(self, type_name: str, type_father_name: str):
        """
        Se le pasa el nombre de type que espera por que sea declarado el padre
        El nombre del padre que se espera que sea declarado
        """
        if type_father_name is None or type_father_name == "":
            return
        """En el caso que el padre sea null"""
        if type_father_name in self.types_name:
            return

        if type_name in self.types_waiting_types_father:
            # Imposible por la gramatica
            raise SemanticError(f'El type {type_name} tiene mas de un padre')
        self.types_waiting_types_father[type_name] = type_father_name

    def is_waiting_father_type(self, type_name: str):
        """
        Retorna True si el type con ese nombre espera por implementar un protocolo o metodo
        """
        return type_name in self.types_waiting_types_father or type_name in self.types_waiting_protocol_father


class MethodScope:
    def __init__(self, type_residence: TypeScope, name_method, vars_: list[VarDefNode]):
        self.vars: dict[str, VarDefNode] = {}
        self.type_residence: TypeScope = type_residence
        self.name: str = name_method
        for var in vars_:
            name = var.id
            if name in self.vars:
                raise SemanticError(
                    f"No se puede definir un método con dos variables con el mismo nombre nombre variable: {name} en el metodo: {name_method}")
            self.vars[name] = var

    def is_attr_define(self, attr_name: str) -> bool:
        return self.type_residence.is_attr_hear_or_heredado(attr_name, self.name)

    def is_var_define(self, var_name: str) -> bool:
        return var_name in self.vars

class FunctionScope:
    def __init__(self, function_decl: FunctionDeclarationNode, global_scope):
        self.name = function_decl.id
        self.func_delc = function_decl
        self.args_ = function_decl.args
        self.body = function_decl.body
        self.global_scope=global_scope
        self.vars: dict[str, VarDefNode]={}
        for var in self.args_:
            name = var.id
            if name in self.vars:
                raise SemanticError(
                    f"No se puede definir  una funcion con dos variables con el mismo nombre nombre variable: {name} en la función: {self.name}")
            self.vars[name] = var

    def is_var_arg(self, var_name: str):
        """
        Devuelve True si el arguamento esta en la definición de la función
             """
        return var_name in self.vars

    def __len__(self):
        return len(self.args_)
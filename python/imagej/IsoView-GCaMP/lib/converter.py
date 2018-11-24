from org.objectweb.asm import ClassWriter, Opcodes, Type
from java.lang import Object, Class
from net.imglib2.converter.readwrite import SamplerConverter
from net.imglib2 import Sampler
from itertools import imap
# Local lib
from lib.asm import initClass, initMethod, initConstructor, CustomClassLoader


def defineSamplerConverter(fromType,
                           toType,
                           classname="",
                           toAccess=None,
                           fromMethod="getRealFloat",
                           fromMethodReturnType="F", # F: native float; if a class, use: "L%s;" % Type.getInternalName(TheClass)
                           toMethod="setReal",
                           toMethodArgType="F"): # F: native float
  """ A class implementing SamplerConverter, in asm for high-performance (25x jython's speed).

      fromType: the source type to convert like e.g. UnsignedByteType.
      toType: the target type, like e.g. FloatType.
      classname: optional, the fully qualified name for the new class implementing SamplerConverter.
      fromMethod: the name of the fromType class method to use for getting its value.
                  Defaults to "getRealFloat" from the RealType interface.
      fromMethodReturnType: a single letter, like:
        'F': float, 'D': double, 'C': char, 'B': byte, 'Z': boolean, 'S': short, 'I': integer, 'J': long
        See: https://gitlab.ow2.org/asm/asm/blob/master/asm/src/main/java/org/objectweb/asm/Frame.java
      toMethod: the name of the toType class method for setting the value.
                Defaults to "setReal" from the RealType interface.
      toMethodArgType: a single letter, like:
        'F': float, 'D': double, 'C': char, 'B': byte, 'Z': boolean, 'S': short, 'I': integer, 'J': long
      toAccess: the interface to implement, such as FloatAccess. Optional, will be guessed. """

  if toAccess is None:
    toTypeName = toType.getSimpleName()
    name = toTypeName[0:toTypeName.rfind("Type")]
    if name.startswith("Unsigned"):
      name = name[8:]
    toAccessName = "net.imglib2.img.basictypeaccess.%sAccess" % name
    toAccess = CustomClassLoader().loadClass("net.imglib2.img.basictypeaccess.%sAccess" % name)

  if "" == classname:
    classname = "asm/converters/%sTo%sSamplerConverter" % (fromType.getSimpleName(), toType.getSimpleName())

  access_classname = "asm/converters/%sTo%sAccess" % (fromType.getSimpleName(), toType.getSimpleName())

  # First *Access class like e.g. FloatAccess
  facc = initClass(access_classname,
                   access=Opcodes.ACC_PUBLIC | Opcodes.ACC_FINAL,
                   interfaces=[toAccess],
                   interfaces_parameters={},
                   with_default_constructor=False)

  # private final "sampler" field
  f = facc.visitField(Opcodes.ACC_PRIVATE | Opcodes.ACC_FINAL,
                      "sampler",
                      "L%s;" % Type.getInternalName(Sampler),
                      "L%s<+L%s;>;" % tuple(imap(Type.getInternalName, (Sampler, fromType))),
                      None)

  # The constructor has to initialize the field "sampler"
  c = initConstructor(facc,
                      descriptor="(Lnet/imglib2/Sampler;)V",
                      signature="(Lnet/imglib2/Sampler<+L%s;>;)V" % Type.getInternalName(fromType))
  # The 'c' constructor already invoked <init>
  # Now onto the rest of the constructor body:
  c.visitVarInsn(Opcodes.ALOAD, 0)
  c.visitVarInsn(Opcodes.ALOAD, 1)
  field = {"classname": access_classname,
           "name": "sampler",
           "descriptor": "Lnet/imglib2/Sampler;"}
  c.visitFieldInsn(Opcodes.PUTFIELD, field["classname"], field["name"], field["descriptor"])
  c.visitInsn(Opcodes.RETURN)
  c.visitMaxs(2, 2)
  c.visitEnd()

  # Declare getValue and setValue methods
  gv = initMethod(facc,
                  "getValue",
                  access=Opcodes.ACC_PUBLIC | Opcodes.ACC_FINAL,
                  descriptor="(I)%s" % toMethodArgType) # e.g. "F" for native float
  gv.visitVarInsn(Opcodes.ALOAD, 0)
  gv.visitFieldInsn(Opcodes.GETFIELD, field["classname"], field["name"], field["descriptor"])
  gv.visitMethodInsn(Opcodes.INVOKEINTERFACE,
                    Type.getInternalName(Sampler),
                    "get",
                    "()L%s;" % Type.getInternalName(Object), # isn't this weird? Why Object?
                    True)
  gv.visitTypeInsn(Opcodes.CHECKCAST, Type.getInternalName(fromType))
  print Type.getInternalName(fromType), fromMethod, fromMethodReturnType
  gv.visitMethodInsn(Opcodes.INVOKEVIRTUAL,
                    Type.getInternalName(fromType),
                    fromMethod, # e.g. getRealFloat
                    "()%s" % fromMethodReturnType, # e.g. F for native float
                    False)
  # Figure out the return and the loading instructions: primitive or object class
  # (NOTE: will not work for array, that starts with '[')
  if fromMethodReturnType in ["F", "D"]: # 'F' for float, 'D' for double
    ret = fromMethodReturnType + "RETURN"
    load = fromMethodReturnType + "LOAD"
  elif 'J' == fromMethodReturnType: # 'J' is for long
    ret = "LRETURN"
    load = "LLOAD"
  elif fromMethodReturnType in ["S", "I", "B", "C", "Z"]: # 'C': char, 'B': byte, 'Z', boolean, 'S', short, 'I': integer
    ret = "IRETURN"
    load = "ILOAD"
  else:
    ret = "ARETURN" # object class
    load = "ALOAD"
  gv.visitInsn(Opcodes.__getattribute__(Opcodes, ret)._doget(Opcodes)) # Opcodes.FRETURN: native float return
  gv.visitMaxs(1, 2)
  gv.visitEnd()

  sv = initMethod(facc,
                  "setValue",
                  access=Opcodes.ACC_PUBLIC | Opcodes.ACC_FINAL,
                  descriptor="(I%s)V" % toMethodArgType) # e.g. "F" for native float
  sv.visitVarInsn(Opcodes.ALOAD, 0)
  sv.visitFieldInsn(Opcodes.GETFIELD, field["classname"], field["name"], field["descriptor"])
  sv.visitMethodInsn(Opcodes.INVOKEINTERFACE,
                    Type.getInternalName(Sampler),
                    "get",
                    "()L%s;" % Type.getInternalName(Object), # isn't this weird? Why Object?
                    True)
  sv.visitTypeInsn(Opcodes.CHECKCAST, Type.getInternalName(fromType))
  sv.visitVarInsn(Opcodes.__getattribute__(Opcodes, load)._doget(Opcodes), 2) # e.g. Opcodes.FLOAD
  sv.visitMethodInsn(Opcodes.INVOKEVIRTUAL,
                    Type.getInternalName(fromType),
                    toMethod, # e.g. setReal
                    "(%s)V" % toMethodArgType, # e.g. 'F' for native float
                    False)
  sv.visitInsn(Opcodes.RETURN)
  sv.visitMaxs(2, 3)
  sv.visitEnd()

  # The SamplerConverter outer class
  cw = initClass(classname,
                 interfaces=[SamplerConverter],
                 interfaces_parameters={SamplerConverter: [fromType, toType]})

  # In the signature, the + sign is for e.g. <? extends UnignedByteType>
  # Here, the signature is the same as the descriptor, but with parameter types
  # descriptor="(Lnet/imglib2/Sampler;)Lnet/imglib2/type/numeric/real/FloatType;"
  # signature="(Lnet/imglib2/Sampler<+Lnet/imglib2/type/numeric/integer/UnsignedByteType;>;)Lnet/imglib2/type/numeric/real/FloatType;",
  m = initMethod(cw, "convert",
                 argument_classes=[Sampler],
                 argument_parameters=[fromType],
                 argument_prefixes=['+'], # '+' means: <? extends UnsignedByteType>
                 return_type=toType)

  m.visitCode()
  m.visitTypeInsn(Opcodes.NEW, Type.getInternalName(toType))
  m.visitInsn(Opcodes.DUP)
  m.visitTypeInsn(Opcodes.NEW, access_classname)
  m.visitInsn(Opcodes.DUP)
  m.visitVarInsn(Opcodes.ALOAD, 1)
  m.visitMethodInsn(Opcodes.INVOKESPECIAL, # invoke new
                    access_classname,
                    "<init>", # constructor
                    "(L%s;)V" % Type.getInternalName(Sampler),
                    False)
  m.visitMethodInsn(Opcodes.INVOKESPECIAL, # create new toType with the *Access as argument
                    Type.getInternalName(toType),
                    "<init>", # constructor
                    "(L%s;)V" % Type.getInternalName(toAccess),
                    False)
  m.visitInsn(Opcodes.ARETURN) # ARETURN: return the object at the top of the stack
  m.visitMaxs(5, 2) # 5 stack slots: the two NEW calls, 1 ALOAD, 2 DUP (I think). And 2 local variables: this, and a method argument.
  m.visitEnd()

  # If bridge is not defined, the above 'convert' method cannot be invoked: would fail with AbstractMethodException
  # To be fair, the TextWriter on the compiled java version of this class did use the bridge.
  # The surprising bit is that, in test_asm_class_generation.py, the bridge is not necessary
  # even though the class is rather similar overall.
  bridge = cw.visitMethod(Opcodes.ACC_PUBLIC | Opcodes.ACC_VOLATILE | Opcodes.ACC_BRIDGE,
                          "convert",
                          "(L%s;)L%s;" % tuple(imap(Type.getInternalName, (Sampler, Object))),
                          None,
                          None)
  bridge.visitCode()
  bridge.visitVarInsn(Opcodes.ALOAD, 0)
  bridge.visitVarInsn(Opcodes.ALOAD, 1)
  bridge.visitMethodInsn(Opcodes.INVOKEVIRTUAL,
                         classname,
                         "convert",
                         "(L%s;)L%s;" % tuple(imap(Type.getInternalName, (Sampler, toType))), # descriptor
                         False)
  bridge.visitInsn(Opcodes.ARETURN)
  bridge.visitMaxs(2, 2)
  bridge.visitEnd()

  # Load both classes
  loader = CustomClassLoader()
  accessClass = loader.defineClass(access_classname, facc.toByteArray())
  samplerClass = loader.defineClass(classname, cw.toByteArray())

  return samplerClass


def createSamplerConverter(*args, **kwargs):
  """ Returns a new instance of the newly defined class implementing the SamplerConverter interface.
      See defineSamplerConverter for all argument details. """
  return defineSamplerConverter(*args, **kwargs).newInstance()


def defineConverter(fromType,
                    toType,
                    classname="",
                    fromMethod="getRealFloat",
                    fromMethodReturnType="F", # e.g. "F" for native float
                    toMethod="setReal",
                    toMethodArgType="F"):
  """ Create a new Converter fromType toType.
  
      fromType: the net.imglib2.Type to see as transformed into toType.
      toType: the net.imglib2.Type to see.
      classname: optional, will be made up if not defined.
      fromMethod: the method for reading the value from the fromType.
                  Defaults to getRealFloat form the RealType interface. 
      toMethod: the method for setting the value to the toType.
                Defaults to setReal from the RealType interface. """

  if "" == classname:
    classname = "asm/converters/%sTo%sConverter" % (fromType.getSimpleName(), toType.getSimpleName())

  class_object = Type.getInternalName(Object)

  # Type I for fromType
  # Type O for toType
  # Object for superclass
  # Converter<I, O> for interface
  class_signature = "<I:L%s;O:L%s;>L%s;L%s<TI;TO;>;" % \
    tuple(imap(Type.getInternalName, (fromType, toType, Object, Converter)))

  # Two arguments, one parameter for each: one for I, and another for O
  # void return type: V
  method_signature = "(TI;TO;)V;"

  cw = ClassWriter(ClassWriter.COMPUTE_FRAMES)
  cw.visit(Opcodes.V1_8,                      # java version
           Opcodes.ACC_PUBLIC,                # public class
           class_name,                        # package and class name
           class_signature,                   # signature (None means not generic)
           class_object,                      # superclass
           [Type.getInternalName(Converter)]) # array of interfaces

  # Default constructor
  constructor = cw.visitMethod(Opcodes.ACC_PUBLIC,  # public
                               "<init>",            # method name
                               "()V",               # descriptor
                               None,                # signature
                               None)                # Exceptions (array of String)

  # ... has to invoke the super() for Object
  constructor.visitCode()
  constructor.visitVarInsn(Opcodes.ALOAD, 0) # load "this" onto the stack: the first local variable is "this"
  constructor.visitMethodInsn(Opcodes.INVOKESPECIAL, # invoke an instance method (non-virtual)
                              class_object,          # class on which the method is defined
                              "<init>",              # name of the method (the default constructor of Object)
                              "()V",                 # descriptor of the default constructor of Object
                              False)                 # not an interface
  constructor.visitInsn(Opcodes.RETURN) # End the constructor method
  constructor.visitMaxs(1, 1) # The maximum number of stack slots (1) and local vars (1: "this")

  # The convert(I, O) method from the Converter interface
  method = cw.visitMethod(Opcodes.ACC_PUBLIC, # public method
                          "convert",          # name of the interface method we are implementing
                          "(L%s;L%s;)V" % tuple(imap(Type.getInternalName, (fromType, toType))), # descriptor
                          "(TI;TO;)",         # signature
                          None)               # Exceptions (array of String)

  method.visitCode()
  method.visitVarInsn(Opcodes.ALOAD, 2) # Load second argument onto stack: the FloatType
  method.visitVarInsn(Opcodes.ALOAD, 1) # Load first argument onto stack: the UnsignedByteType
  method.visitMethodInsn(Opcodes.INVOKEVIRTUAL,
                         Type.getInternalName(fromType),
                         fromMethod, # e.g. "getRealFloat"
                         "()%s" % fromMethodReturnType, # descriptor: no arguments # e.g. "F" for native float
                         False)
  method.visitMethodInsn(Opcodes.INVOKEVIRTUAL,
                         Type.getInternalName(toType),
                         toMethod, # e.g. "setReal"
                         "(%s)V" % toMethodArgType, # e.g. "F" for native float
                         False)
  method.visitInsn(Opcodes.RETURN)
  method.visitMaxs(2, 3) # 2 stack slots: the two ALOAD calls. And 3 local variables: this, and two method arguments.
  method.visitEnd()

  # Now the public volatile bridge, because the above method uses generics.
  # Does not seem to be necessary to run the convert method.
  # This method takes an (Object, Object) as arguments and casts them to the expected types,
  # and then invokes the above typed version of the "convert" method.
  # The only reason I am adding it here is because I saw it when I printed the class byte code,
  # after writing the converter in java and using this command to see the asm code:
  # $ java -classpath /home/albert/Programming/fiji-new/Fiji.app/jars/imglib2-5.1.0.jar:/home/albert/Programming/fiji-new/Fiji.app/jars/asm-5.0.4.jar://home/albert/Programming/fiji-new/Fiji.app/jars/asm-util-4.0.jar org.objectweb.asm.util.Textifier my/UnsignedByteToFloatConverter.class

  bridge = cw.visitMethod(Opcodes.ACC_PUBLIC | Opcodes.ACC_SYNTHETIC | Opcodes.ACC_BRIDGE,
                          "convert",
                          "(L%s;L%s;)V" % tuple(repeat(class_object, 2)),
                          "(L%s;L%s;)V" % tuple(repeat(class_object, 2)),
                          None)
  bridge.visitCode()
  bridge.visitVarInsn(Opcodes.ALOAD, 0)
  bridge.visitVarInsn(Opcodes.ALOAD, 1)
  bridge.visitTypeInsn(Opcodes.CHECKCAST, Type.getInternalName(fromType))
  bridge.visitVarInsn(Opcodes.ALOAD, 2)
  bridge.visitTypeInsn(Opcodes.CHECKCAST, Type.getInternalName(toType))
  bridge.visitMethodInsn(Opcodes.INVOKEVIRTUAL,
                         class_name,
                         "convert",
                         "(L%s;L%s;)V" % tuple(imap(Type.getInternalName, (fromType, toType))), # descriptor
                         False)
  bridge.visitInsn(Opcodes.RETURN)
  bridge.visitMaxs(3, 3)
  bridge.visitEnd()

  loader = CustomClassLoader()
  converterClass = loader.defineClass(classname, cw.toByteArray())

  return converterClass


def createConverter(*args, **kwargs):
  """ Returns a new instance of the newly defined class implementing the Converter interface.
      See defineConverter for all argument details. """
  return defineSConverter(*args, **kwargs).newInstance()

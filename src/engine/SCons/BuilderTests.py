#
# __COPYRIGHT__
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY
# KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

__revision__ = "__FILE__ __REVISION__ __DATE__ __DEVELOPER__"

# Define a null function for use as a builder action.
# Where this is defined in the file seems to affect its
# byte-code contents, so try to minimize changes by
# defining it here, before we even import anything.
def Func():
    pass

import os.path
import sys
import types
import unittest

import TestCmd

import SCons.Action
import SCons.Builder
import SCons.Environment
import SCons.Errors

# Initial setup of the common environment for all tests,
# a temporary working directory containing a
# script for writing arguments to an output file.
#
# We don't do this as a setUp() method because it's
# unnecessary to create a separate directory and script
# for each test, they can just use the one.
test = TestCmd.TestCmd(workdir = '')

outfile = test.workpath('outfile')
outfile2 = test.workpath('outfile2')

show_string = None

scons_env = SCons.Environment.Environment()

env_arg2nodes_called = None

class Environment:
    def __init__(self, **kw):
        self.d = {}
        self.d['SHELL'] = scons_env['SHELL']
        self.d['SPAWN'] = scons_env['SPAWN']
        self.d['ESCAPE'] = scons_env['ESCAPE']
        for k, v in kw.items():
            self.d[k] = v
        global env_arg2nodes_called
        env_arg2nodes_called = None
        self.scanner = None
    def subst(self, s):
        if not SCons.Util.is_String(s):
            return s
        try:
            if s[0] == '$':
                return self.d.get(s[1:], '')
            if s[1] == '$':
                return s[0] + self.d.get(s[2:], '')
        except IndexError:
            pass
        return self.d.get(s, s)
    def arg2nodes(self, args, factory):
        global env_arg2nodes_called
        env_arg2nodes_called = 1
        if not SCons.Util.is_List(args):
            args = [args]
        list = []
        for a in args:
            if SCons.Util.is_String(a):
                a = factory(a)
            list.append(a)
        return list
    def get_scanner(self, ext):
        return self.scanner
    def Dictionary(self):
        return {}
    def autogenerate(self, dir=''):
        return {}
    def __setitem__(self, item, var):
        self.d[item] = var
    def __getitem__(self, item):
        return self.d[item]
    def has_key(self, item):
        return self.d.has_key(item)
    def keys(self):
        return self.d.keys()
    def get(self, key, value):
        return self.d.get(key, value)
    def Override(self, overrides):
        env = apply(Environment, (), self.d)
        env.d.update(overrides)
        return env
    def items(self):
        return self.d.items()
    def sig_dict(self):
        d = {}
        for k,v in self.items(): d[k] = v
        d['TARGETS'] = ['__t1__', '__t2__', '__t3__', '__t4__', '__t5__', '__t6__']
        d['TARGET'] = d['TARGETS'][0]
        d['SOURCES'] = ['__s1__', '__s2__', '__s3__', '__s4__', '__s5__', '__s6__']
        d['SOURCE'] = d['SOURCES'][0]
        return d

class MyNode_without_target_from_source:
    def __init__(self, name):
        self.name = name
        self.sources = []
        self.builder = None
        self.side_effect = 0
        self.source_scanner = None
    def __str__(self):
        return self.name
    def builder_set(self, builder):
        self.builder = builder
    def has_builder(self):
        return not self.builder is None
    def env_set(self, env, safe=0):
        self.env = env
    def add_source(self, source):
        self.sources.extend(source)
    def scanner_key(self):
        return self.name
    def is_derived(self):
        return self.has_builder()
    def generate_build_env(self, env):
        return env
    def get_build_env(self):
        return self.executor.get_build_env()
    def set_executor(self, executor):
        self.executor = executor
    def get_executor(self, create=1):
        return self.executor

class MyNode(MyNode_without_target_from_source):
    def target_from_source(self, prefix, suffix, stripext):
        return MyNode(prefix + stripext(str(self))[0] + suffix)

class BuilderTestCase(unittest.TestCase):

    def test__nonzero__(self):
        """Test a builder raising an exception when __nonzero__ is called
        """
        builder = SCons.Builder.Builder(action="foo")
        exc_caught = None
        try:
            builder.__nonzero__()
        except SCons.Errors.InternalError:
            exc_caught = 1
        assert exc_caught, "did not catch expected InternalError exception"

        class Node:
             pass

        n = Node()
        n.builder = builder
        exc_caught = None
        try:
            if n.builder:
                pass
        except SCons.Errors.InternalError:
            exc_caught = 1
        assert exc_caught, "did not catch expected InternalError exception"

    def test__call__(self):
        """Test calling a builder to establish source dependencies
        """
        env = Environment()
        builder = SCons.Builder.Builder(action="foo", node_factory=MyNode)

        n1 = MyNode("n1");
        n2 = MyNode("n2");
        builder(env, target = n1, source = n2)
        assert env_arg2nodes_called
        assert n1.env == env, n1.env
        assert n1.builder == builder, n1.builder
        assert n1.sources == [n2], n1.sources
        assert n1.executor, "no executor found"
        assert not hasattr(n2, 'env')

        target = builder(env, target = 'n3', source = 'n4')
        assert target.name == 'n3'
        assert target.sources[0].name == 'n4'

        target = builder(env, target = 'n4 n5', source = ['n6 n7'])
        assert target.name == 'n4 n5'
        assert target.sources[0].name == 'n6 n7'

        target = builder(env, target = ['n8 n9'], source = 'n10 n11')
        assert target.name == 'n8 n9'
        assert target.sources[0].name == 'n10 n11'

        # A test to be uncommented when we freeze the environment
        # as part of calling the builder.
        #env1 = Environment(VAR='foo')
        #target = builder(env1, target = 'n12', source = 'n13')
        #env1['VAR'] = 'bar'
        #be = target.get_build_env()
        #assert be['VAR'] == 'foo', be['VAR']

        if not hasattr(types, 'UnicodeType'):
            uni = str
        else:
            uni = unicode

        target = builder(env, target = uni('n12 n13'),
                          source = [uni('n14 n15')])
        assert target.name == uni('n12 n13')
        assert target.sources[0].name == uni('n14 n15')

        target = builder(env, target = [uni('n16 n17')],
                         source = uni('n18 n19'))
        assert target.name == uni('n16 n17')
        assert target.sources[0].name == uni('n18 n19')

        n20 = MyNode_without_target_from_source('n20')
        flag = 0
        try:
            target = builder(env, source=n20)
        except SCons.Errors.UserError, e:
            flag = 1
        assert flag, "UserError should be thrown if a source node can't create a target."

        builder = SCons.Builder.Builder(action="foo",
                                        node_factory=MyNode,
                                        prefix='p-',
                                        suffix='.s')
        target = builder(env, source='n21')
        assert target.name == 'p-n21.s', target

    def test_action(self):
        """Test Builder creation

        Verify that we can retrieve the supplied action attribute.
        """
        builder = SCons.Builder.Builder(action="foo")
        assert builder.action.cmd_list == "foo"

        def func():
            pass
        builder = SCons.Builder.Builder(action=func)
        assert isinstance(builder.action, SCons.Action.FunctionAction)
        # Preserve the following so that the baseline test will fail.
        # Remove it in favor of the previous test at some convenient
        # point in the future.
        assert builder.action.execfunction == func

    def test_generator(self):
        """Test Builder creation given a generator function."""

        def generator():
            pass

        builder = SCons.Builder.Builder(generator=generator)
        assert builder.action.generator == generator

    def test_cmp(self):
        """Test simple comparisons of Builder objects
        """
        b1 = SCons.Builder.Builder(src_suffix = '.o')
        b2 = SCons.Builder.Builder(src_suffix = '.o')
        assert b1 == b2
        b3 = SCons.Builder.Builder(src_suffix = '.x')
        assert b1 != b3
        assert b2 != b3

    def test_node_factory(self):
        """Test a Builder that creates nodes of a specified class
        """
        class Foo:
            pass
        def FooFactory(target):
            global Foo
            return Foo(target)
        builder = SCons.Builder.Builder(node_factory = FooFactory)
        assert builder.target_factory is FooFactory
        assert builder.source_factory is FooFactory

    def test_target_factory(self):
        """Test a Builder that creates target nodes of a specified class
        """
        class Foo:
            pass
        def FooFactory(target):
            global Foo
            return Foo(target)
        builder = SCons.Builder.Builder(target_factory = FooFactory)
        assert builder.target_factory is FooFactory
        assert not builder.source_factory is FooFactory

    def test_source_factory(self):
        """Test a Builder that creates source nodes of a specified class
        """
        class Foo:
            pass
        def FooFactory(source):
            global Foo
            return Foo(source)
        builder = SCons.Builder.Builder(source_factory = FooFactory)
        assert not builder.target_factory is FooFactory
        assert builder.source_factory is FooFactory

    def test_splitext(self):
        """Test the splitext() method attached to a Builder."""
        b = SCons.Builder.Builder()
        assert b.splitext('foo') == ('foo','')
        assert b.splitext('foo.bar') == ('foo','.bar')
        assert b.splitext(os.path.join('foo.bar', 'blat')) == (os.path.join('foo.bar', 'blat'),'')

        class MyBuilder(SCons.Builder.BuilderBase):
            def splitext(self, path):
                return "called splitext()"

        b = MyBuilder()
        ret = b.splitext('xyz.c')
        assert ret == "called splitext()", ret

    def test_adjust_suffix(self):
        """Test how a Builder adjusts file suffixes
        """
        b = SCons.Builder.Builder()
        assert b.adjust_suffix('.foo') == '.foo'
        assert b.adjust_suffix('foo') == '.foo'
        assert b.adjust_suffix('$foo') == '$foo'

        class MyBuilder(SCons.Builder.BuilderBase):
            def adjust_suffix(self, suff):
                return "called adjust_suffix()"

        b = MyBuilder()
        ret = b.adjust_suffix('.foo')
        assert ret == "called adjust_suffix()", ret

    def test_prefix(self):
        """Test Builder creation with a specified target prefix

        Make sure that there is no '.' separator appended.
        """
        env = Environment()
        builder = SCons.Builder.Builder(prefix = 'lib.')
        assert builder.get_prefix(env) == 'lib.'
        builder = SCons.Builder.Builder(prefix = 'lib')
        assert builder.get_prefix(env) == 'lib'
        tgt = builder(env, target = 'tgt1', source = 'src1')
        assert tgt.path == 'libtgt1', \
                "Target has unexpected name: %s" % tgt.path
        tgt = builder(env, target = 'tgt2a tgt2b', source = 'src2')
        assert tgt.path == 'libtgt2a tgt2b', \
                "Target has unexpected name: %s" % tgt.path
        tgt = builder(env, source = 'src3')
        assert tgt.path == 'libsrc3', \
                "Target has unexpected name: %s" % tgt.path
        tgt = builder(env, source = 'lib/src4')
        assert tgt.path == os.path.join('lib', 'libsrc4'), \
                "Target has unexpected name: %s" % tgt.path
        tgt = builder(env, target = 'lib/tgt5', source = 'lib/src5')
        assert tgt.path == os.path.join('lib', 'libtgt5'), \
                "Target has unexpected name: %s" % tgt.path

        def gen_prefix(env, sources):
            return "gen_prefix() says " + env['FOO']
        my_env = Environment(FOO = 'xyzzy')
        builder = SCons.Builder.Builder(prefix = gen_prefix)
        assert builder.get_prefix(my_env) == "gen_prefix() says xyzzy"
        my_env['FOO'] = 'abracadabra'
        assert builder.get_prefix(my_env) == "gen_prefix() says abracadabra"

        def my_emit(env, sources):
            return env.subst('$EMIT')
        my_env = Environment(FOO = '.foo', EMIT = 'emit-')
        builder = SCons.Builder.Builder(prefix = {None   : 'default-',
                                                  '.in'  : 'out-',
                                                  '.x'   : 'y-',
                                                  '$FOO' : 'foo-',
                                                  '.zzz' : my_emit})
        tgt = builder(my_env, source = 'f1')
        assert tgt.path == 'default-f1', tgt.path
        tgt = builder(my_env, source = 'f2.c')
        assert tgt.path == 'default-f2', tgt.path
        tgt = builder(my_env, source = 'f3.in')
        assert tgt.path == 'out-f3', tgt.path
        tgt = builder(my_env, source = 'f4.x')
        assert tgt.path == 'y-f4', tgt.path
        tgt = builder(my_env, source = 'f5.foo')
        assert tgt.path == 'foo-f5', tgt.path
        tgt = builder(my_env, source = 'f6.zzz')
        assert tgt.path == 'emit-f6', tgt.path

    def test_src_suffix(self):
        """Test Builder creation with a specified source file suffix
        
        Make sure that the '.' separator is appended to the
        beginning if it isn't already present.
        """
        env = Environment(XSUFFIX = '.x', YSUFFIX = '.y')

        b1 = SCons.Builder.Builder(src_suffix = '.c')
        assert b1.src_suffixes(env) == ['.c'], b1.src_suffixes(env)

        tgt = b1(env, target = 'tgt2', source = 'src2')
        assert tgt.sources[0].path == 'src2.c', \
                "Source has unexpected name: %s" % tgt.sources[0].path

        tgt = b1(env, target = 'tgt3', source = 'src3a src3b')
        assert len(tgt.sources) == 1
        assert tgt.sources[0].path == 'src3a src3b.c', \
                "Unexpected tgt.sources[0] name: %s" % tgt.sources[0].path

        b2 = SCons.Builder.Builder(src_suffix = '.2', src_builder = b1)
        assert b2.src_suffixes(env) == ['.2', '.c'], b2.src_suffixes(env)

        b3 = SCons.Builder.Builder(action = {'.3a' : '', '.3b' : ''})
        s = b3.src_suffixes(env)
        s.sort()
        assert s == ['.3a', '.3b'], s

        b4 = SCons.Builder.Builder(src_suffix = '$XSUFFIX')
        assert b4.src_suffixes(env) == ['.x'], b4.src_suffixes(env)

        b5 = SCons.Builder.Builder(action = { '.y' : ''})
        assert b5.src_suffixes(env) == ['.y'], b5.src_suffixes(env)

    def test_suffix(self):
        """Test Builder creation with a specified target suffix

        Make sure that the '.' separator is appended to the
        beginning if it isn't already present.
        """
        env = Environment()
        builder = SCons.Builder.Builder(suffix = '.o')
        assert builder.get_suffix(env) == '.o', builder.get_suffix(env)
        builder = SCons.Builder.Builder(suffix = 'o')
        assert builder.get_suffix(env) == '.o', builder.get_suffix(env)
        tgt = builder(env, target = 'tgt3', source = 'src3')
        assert tgt.path == 'tgt3.o', \
                "Target has unexpected name: %s" % tgt.path
        tgt = builder(env, target = 'tgt4a tgt4b', source = 'src4')
        assert tgt.path == 'tgt4a tgt4b.o', \
                "Target has unexpected name: %s" % tgt.path
        tgt = builder(env, source = 'src5')
        assert tgt.path == 'src5.o', \
                "Target has unexpected name: %s" % tgt.path

        def gen_suffix(env, sources):
            return "gen_suffix() says " + env['BAR']
        my_env = Environment(BAR = 'hocus pocus')
        builder = SCons.Builder.Builder(suffix = gen_suffix)
        assert builder.get_suffix(my_env) == "gen_suffix() says hocus pocus", builder.get_suffix(my_env)
        my_env['BAR'] = 'presto chango'
        assert builder.get_suffix(my_env) == "gen_suffix() says presto chango"

        def my_emit(env, sources):
            return env.subst('$EMIT')
        my_env = Environment(BAR = '.bar', EMIT = '.emit')
        builder = SCons.Builder.Builder(suffix = {None   : '.default',
                                                  '.in'  : '.out',
                                                  '.x'   : '.y',
                                                  '$BAR' : '.new',
                                                  '.zzz' : my_emit})
        tgt = builder(my_env, source = 'f1')
        assert tgt.path == 'f1.default', tgt.path
        tgt = builder(my_env, source = 'f2.c')
        assert tgt.path == 'f2.default', tgt.path
        tgt = builder(my_env, source = 'f3.in')
        assert tgt.path == 'f3.out', tgt.path
        tgt = builder(my_env, source = 'f4.x')
        assert tgt.path == 'f4.y', tgt.path
        tgt = builder(my_env, source = 'f5.bar')
        assert tgt.path == 'f5.new', tgt.path
        tgt = builder(my_env, source = 'f6.zzz')
        assert tgt.path == 'f6.emit', tgt.path

    def test_ListBuilder(self):
        """Testing ListBuilder class."""
        def function2(target, source, env, tlist = [outfile, outfile2], **kw):
            for t in target:
                open(str(t), 'w').write("function2\n")
            for t in tlist:
                if not t in map(str, target):
                    open(t, 'w').write("function2\n")
            return 1

        env = Environment()
        builder = SCons.Builder.Builder(action = function2)
        tgts = builder(env, target = [outfile, outfile2], source = 'foo')
        for t in tgts:
            t.prepare()
        try:
            tgts[0].build()
        except SCons.Errors.BuildError:
            pass
        c = test.read(outfile, 'r')
        assert c == "function2\n", c
        c = test.read(outfile2, 'r')
        assert c == "function2\n", c

        sub1_out = test.workpath('sub1', 'out')
        sub2_out = test.workpath('sub2', 'out')

        def function3(target, source, env, tlist = [sub1_out, sub2_out]):
            for t in target:
                open(str(t), 'w').write("function3\n")
            for t in tlist:
                if not t in map(str, target):
                    open(t, 'w').write("function3\n")
            return 1

        builder = SCons.Builder.Builder(action = function3)
        tgts = builder(env, target = [sub1_out, sub2_out], source = 'foo')
        for t in tgts:
            t.prepare()
        try:
            tgts[0].build()
        except SCons.Errors.BuildError:
            pass
        c = test.read(sub1_out, 'r')
        assert c == "function3\n", c
        c = test.read(sub2_out, 'r')
        assert c == "function3\n", c
        assert os.path.exists(test.workpath('sub1'))
        assert os.path.exists(test.workpath('sub2'))

    def test_MultiStepBuilder(self):
        """Testing MultiStepBuilder class."""
        env = Environment()
        builder1 = SCons.Builder.Builder(action='foo',
                                         src_suffix='.bar',
                                         suffix='.foo')
        builder2 = SCons.Builder.MultiStepBuilder(action='bar',
                                                  src_builder = builder1,
                                                  src_suffix = '.foo')

        tgt = builder2(env, target='baz', source=['test.bar', 'test2.foo', 'test3.txt'])
        assert str(tgt.sources[0]) == 'test.foo', str(tgt.sources[0])
        assert str(tgt.sources[0].sources[0]) == 'test.bar', \
               str(tgt.sources[0].sources[0])
        assert str(tgt.sources[1]) == 'test2.foo', str(tgt.sources[1])
        assert str(tgt.sources[2]) == 'test3.txt', str(tgt.sources[2])

        tgt = builder2(env, 'aaa.bar')
        assert str(tgt) == 'aaa', str(tgt)
        assert str(tgt.sources[0]) == 'aaa.foo', str(tgt.sources[0])
        assert str(tgt.sources[0].sources[0]) == 'aaa.bar', \
               str(tgt.sources[0].sources[0])

        builder3 = SCons.Builder.MultiStepBuilder(action = 'foo',
                                                  src_builder = 'xyzzy',
                                                  src_suffix = '.xyzzy')
        assert builder3.get_src_builders(Environment()) == []

        builder4 = SCons.Builder.Builder(action='bld4',
                                         src_suffix='.i',
                                         suffix='_wrap.c')
        builder5 = SCons.Builder.MultiStepBuilder(action='bld5',
                                                  src_builder=builder4,
                                                  suffix='.obj',
                                                  src_suffix='.c')
        builder6 = SCons.Builder.MultiStepBuilder(action='bld6',
                                                  src_builder=builder5,
                                                  suffix='.exe',
                                                  src_suffix='.obj')
        tgt = builder6(env, 'test', 'test.i')
        assert str(tgt) == 'test.exe', str(tgt)
        assert str(tgt.sources[0]) == 'test_wrap.obj', str(tgt.sources[0])
        assert str(tgt.sources[0].sources[0]) == 'test_wrap.c', \
               str(tgt.sources[0].sources[0])
        assert str(tgt.sources[0].sources[0].sources[0]) == 'test.i', \
               str(tgt.sources[0].sources[0].sources[0])
        
    def test_CompositeBuilder(self):
        """Testing CompositeBuilder class."""
        def func_action(target, source, env):
            return 0
        
        env = Environment(BAR_SUFFIX = '.BAR2', FOO_SUFFIX = '.FOO2')
        builder = SCons.Builder.Builder(action={ '.foo' : func_action,
                                                 '.bar' : func_action,
                                                 '$BAR_SUFFIX' : func_action,
                                                 '$FOO_SUFFIX' : func_action })
        
        assert isinstance(builder, SCons.Builder.CompositeBuilder)
        assert isinstance(builder.action, SCons.Action.CommandGeneratorAction)
        tgt = builder(env, target='test1', source='test1.foo')
        assert isinstance(tgt.builder, SCons.Builder.BuilderBase)
        assert tgt.builder.action is builder.action
        tgt = builder(env, target='test2', source='test1.bar')
        assert isinstance(tgt.builder, SCons.Builder.BuilderBase)
        assert tgt.builder.action is builder.action
        flag = 0
        tgt = builder(env, target='test3', source=['test2.bar', 'test1.foo'])
        try:
            tgt.build()
        except SCons.Errors.UserError, e:
            flag = 1
        assert flag, "UserError should be thrown when we build targets with files of different suffixes."
        match = str(e) == "While building `['test3']' from `test1.foo': Cannot build multiple sources with different extensions: .bar, .foo"
        assert match, e

        tgt = builder(env, target='test4', source=['test4.BAR2'])
        assert isinstance(tgt.builder, SCons.Builder.BuilderBase)
        try:
            tgt.build()
            flag = 1
        except SCons.Errors.UserError, e:
            print e
            flag = 0
        assert flag, "It should be possible to define actions in composite builders using variables."
        env['FOO_SUFFIX'] = '.BAR2'
        builder.add_action('$NEW_SUFFIX', func_action)
        flag = 0
        tgt = builder(env, target='test5', source=['test5.BAR2'])
        try:
            tgt.build()
        except SCons.Errors.UserError:
            flag = 1
        assert flag, "UserError should be thrown when we build targets with ambigous suffixes."
        del env.d['FOO_SUFFIX']
        del env.d['BAR_SUFFIX']

        foo_bld = SCons.Builder.Builder(action = 'a-foo',
                                        src_suffix = '.ina',
                                        suffix = '.foo')
        assert isinstance(foo_bld, SCons.Builder.BuilderBase)
        builder = SCons.Builder.Builder(action = { '.foo' : 'foo',
                                                   '.bar' : 'bar' },
                                        src_builder = foo_bld)
        assert isinstance(builder, SCons.Builder.CompositeBuilder)
        assert isinstance(builder.action, SCons.Action.CommandGeneratorAction)

        tgt = builder(env, target='t1', source='t1a.ina t1b.ina')
        assert isinstance(tgt.builder, SCons.Builder.BuilderBase)

        tgt = builder(env, target='t2', source='t2a.foo t2b.ina')
        assert isinstance(tgt.builder, SCons.Builder.MultiStepBuilder), tgt.builder.__dict__

        bar_bld = SCons.Builder.Builder(action = 'a-bar',
                                        src_suffix = '.inb',
                                        suffix = '.bar')
        assert isinstance(bar_bld, SCons.Builder.BuilderBase)
        builder = SCons.Builder.Builder(action = { '.foo' : 'foo'},
                                        src_builder = [foo_bld, bar_bld])
        assert isinstance(builder, SCons.Builder.CompositeBuilder)
        assert isinstance(builder.action, SCons.Action.CommandGeneratorAction)

        builder.add_action('.bar', 'bar')

        tgt = builder(env, target='t3-foo', source='t3a.foo t3b.ina')
        assert isinstance(tgt.builder, SCons.Builder.MultiStepBuilder)

        tgt = builder(env, target='t3-bar', source='t3a.bar t3b.inb')
        assert isinstance(tgt.builder, SCons.Builder.MultiStepBuilder)

        flag = 0
        tgt = builder(env, target='t5', source=['test5a.foo', 'test5b.inb'])
        try:
            tgt.build()
        except SCons.Errors.UserError, e:
            flag = 1
        assert flag, "UserError should be thrown when we build targets with files of different suffixes."
        match = str(e) == "While building `['t5']' from `test5b.bar': Cannot build multiple sources with different extensions: .foo, .bar"
        assert match, e

        flag = 0
        tgt = builder(env, target='t6', source=['test6a.bar', 'test6b.ina'])
        try:
            tgt.build()
        except SCons.Errors.UserError, e:
            flag = 1
        assert flag, "UserError should be thrown when we build targets with files of different suffixes."
        match = str(e) == "While building `['t6']' from `test6b.foo': Cannot build multiple sources with different extensions: .bar, .foo"
        assert match, e

        flag = 0
        tgt = builder(env, target='t4', source=['test4a.ina', 'test4b.inb'])
        try:
            tgt.build()
        except SCons.Errors.UserError, e:
            flag = 1
        assert flag, "UserError should be thrown when we build targets with files of different suffixes."
        match = str(e) == "While building `['t4']' from `test4b.bar': Cannot build multiple sources with different extensions: .foo, .bar"
        assert match, e

        flag = 0
        tgt = builder(env, target='t7', source=['test7'])
        try:
            tgt.build()
        except SCons.Errors.UserError, e:
            flag = 1
        assert flag, "UserError should be thrown when we build targets with files of different suffixes."
        match = str(e) == "While building `['t7']': Cannot deduce file extension from source files: ['test7']"
        assert match, e

        flag = 0
        tgt = builder(env, target='t8', source=['test8.unknown'])
        try:
            tgt.build()
        except SCons.Errors.UserError, e:
            flag = 1
        assert flag, "UserError should be thrown when we build targets with files of different suffixes."
        match = str(e) == "While building `['t8']': Don't know how to build a file with suffix `.unknown'."
        assert match, e

    def test_build_scanner(self):
        """Testing ability to set a target scanner through a builder."""
        global instanced
        class TestScanner:
            pass
        scn = TestScanner()
        env = Environment()
        builder = SCons.Builder.Builder(scanner=scn)
        tgt = builder(env, target='foo2', source='bar')
        assert tgt.target_scanner == scn, tgt.target_scanner

        builder1 = SCons.Builder.Builder(action='foo',
                                         src_suffix='.bar',
                                         suffix='.foo')
        builder2 = SCons.Builder.Builder(action='foo',
                                         src_builder = builder1,
                                         scanner = scn)
        tgt = builder2(env, target='baz2', source='test.bar test2.foo test3.txt')
        assert tgt.target_scanner == scn, tgt.target_scanner

    def test_src_scanner(slf):
        """Testing ability to set a source file scanner through a builder."""
        class TestScanner:
            def key(self, env):
                 return 'TestScannerkey'
            def instance(self, env):
                 return self

        scanner = TestScanner()
        builder = SCons.Builder.Builder(action='action')

        # With no scanner specified, source_scanner is None.
        env1 = Environment()
        tgt = builder(env1, target='foo1.x', source='bar.y')
        src = tgt.sources[0]
        assert tgt.target_scanner != scanner, tgt.target_scanner
        assert src.source_scanner is None, src.source_scanner

        # Later use of the same source file with an environment that
        # has a scanner must still set the scanner.
        env2 = Environment()
        env2.scanner = scanner
        tgt = builder(env2, target='foo2.x', source='bar.y')
        src = tgt.sources[0]
        assert tgt.target_scanner != scanner, tgt.target_scanner
        assert src.source_scanner == scanner, src.source_scanner

    def test_Builder_Args(self):
        """Testing passing extra args to a builder."""
        def buildFunc(target, source, env, s=self):
            s.foo=env['foo']
            s.bar=env['bar']
            assert env['CC'] == 'mycc'

        env=Environment(CC='cc')

        builder = SCons.Builder.Builder(action=buildFunc)
        tgt = builder(env, target='foo', source='bar', foo=1, bar=2, CC='mycc')
        tgt.build()
        assert self.foo == 1, self.foo
        assert self.bar == 2, self.bar

    def test_emitter(self):
        """Test emitter functions."""
        def emit(target, source, env):
            foo = env.get('foo', 0)
            bar = env.get('bar', 0)
            for t in target:
                assert isinstance(t, MyNode)
                assert t.has_builder()
            for s in source:
                assert isinstance(s, MyNode)
            if foo:
                target.append("bar%d"%foo)
            if bar:
                source.append("baz")
            return ( target, source )

        env = Environment()
        builder = SCons.Builder.Builder(action='foo',
                                        emitter=emit,
                                        node_factory=MyNode)
        tgt = builder(env, target='foo2', source='bar')
        assert str(tgt) == 'foo2', str(tgt)
        assert str(tgt.sources[0]) == 'bar', str(tgt.sources[0])

        tgt = builder(env, target='foo3', source='bar', foo=1)
        assert len(tgt) == 2, len(tgt)
        assert 'foo3' in map(str, tgt), map(str, tgt)
        assert 'bar1' in map(str, tgt), map(str, tgt)

        tgt = builder(env, target='foo4', source='bar', bar=1)
        assert str(tgt) == 'foo4', str(tgt)
        assert len(tgt.sources) == 2, len(tgt.sources)
        assert 'baz' in map(str, tgt.sources), map(str, tgt.sources)
        assert 'bar' in map(str, tgt.sources), map(str, tgt.sources)

        env2=Environment(FOO=emit)
        builder2=SCons.Builder.Builder(action='foo',
                                       emitter="$FOO",
                                       node_factory=MyNode)

        tgt = builder2(env2, target='foo5', source='bar')
        assert str(tgt) == 'foo5', str(tgt)
        assert str(tgt.sources[0]) == 'bar', str(tgt.sources[0])

        tgt = builder2(env2, target='foo6', source='bar', foo=2)
        assert len(tgt) == 2, len(tgt)
        assert 'foo6' in map(str, tgt), map(str, tgt)
        assert 'bar2' in map(str, tgt), map(str, tgt)

        tgt = builder2(env2, target='foo7', source='bar', bar=1)
        assert str(tgt) == 'foo7', str(tgt)
        assert len(tgt.sources) == 2, len(tgt.sources)
        assert 'baz' in map(str, tgt.sources), map(str, tgt.sources)
        assert 'bar' in map(str, tgt.sources), map(str, tgt.sources)

        builder2a=SCons.Builder.Builder(action='foo',
                                        emitter="$FOO",
                                        node_factory=MyNode)
        assert builder2 == builder2a, repr(builder2.__dict__) + "\n" + repr(builder2a.__dict__)

        # Test that, if an emitter sets a builder on the passed-in
        # targets and passes back new targets, the new builder doesn't
        # get overwritten.
        new_builder = SCons.Builder.Builder(action='new')
        node = MyNode('foo8')
        new_node = MyNode('foo8.new')
        def emit3(target, source, env, nb=new_builder, nn=new_node):
            for t in target:
                t.builder = nb
            return [nn], source
            
        builder3=SCons.Builder.Builder(action='foo',
                                       emitter=emit3,
                                       node_factory=MyNode)
        tgt = builder3(env, target=node, source='bar')
        assert tgt is new_node, tgt
        assert tgt.builder is builder3, tgt.builder
        assert node.builder is new_builder, node.builder

        # Test use of a dictionary mapping file suffixes to
        # emitter functions
        def emit4a(target, source, env):
            source = map(str, source)
            target = map(lambda x: 'emit4a-' + x[:-3], source)
            return (target, source)
        def emit4b(target, source, env):
            source = map(str, source)
            target = map(lambda x: 'emit4b-' + x[:-3], source)
            return (target, source)
        builder4 = SCons.Builder.Builder(action='foo',
                                         emitter={'.4a':emit4a,
                                                  '.4b':emit4b},
                                         node_factory=MyNode)
        tgt = builder4(env, source='aaa.4a')
        assert str(tgt) == 'emit4a-aaa', str(tgt)
        tgt = builder4(env, source='bbb.4b')
        assert str(tgt) == 'emit4b-bbb', str(tgt)
        tgt = builder4(env, source='ccc.4c')
        assert str(tgt) == 'ccc', str(tgt)

        def emit4c(target, source, env):
            source = map(str, source)
            target = map(lambda x: 'emit4c-' + x[:-3], source)
            return (target, source)
        builder4.add_emitter('.4c', emit4c)
        tgt = builder4(env, source='ccc.4c')
        assert str(tgt) == 'emit4c-ccc', str(tgt)

    def test_no_target(self):
        """Test deducing the target from the source."""

        env = Environment()
        b = SCons.Builder.Builder(action='foo', suffix='.o')

        tgt = b(env, 'aaa')
        assert str(tgt) == 'aaa.o', str(tgt)
        assert len(tgt.sources) == 1, map(str, tgt.sources)
        assert str(tgt.sources[0]) == 'aaa', map(str, tgt.sources)

        tgt = b(env, 'bbb.c')
        assert str(tgt) == 'bbb.o', str(tgt)
        assert len(tgt.sources) == 1, map(str, tgt.sources)
        assert str(tgt.sources[0]) == 'bbb.c', map(str, tgt.sources)

        tgt = b(env, 'ccc.x.c')
        assert str(tgt) == 'ccc.x.o', str(tgt)
        assert len(tgt.sources) == 1, map(str, tgt.sources)
        assert str(tgt.sources[0]) == 'ccc.x.c', map(str, tgt.sources)

        tgt = b(env, ['d0.c', 'd1.c'])
        assert str(tgt) == 'd0.o', str(tgt)
        assert len(tgt.sources) == 2,  map(str, tgt.sources)
        assert str(tgt.sources[0]) == 'd0.c', map(str, tgt.sources)
        assert str(tgt.sources[1]) == 'd1.c', map(str, tgt.sources)

        tgt = b(env, source='eee')
        assert str(tgt) == 'eee.o', str(tgt)
        assert len(tgt.sources) == 1, map(str, tgt.sources)
        assert str(tgt.sources[0]) == 'eee', map(str, tgt.sources)

        tgt = b(env, source='fff.c')
        assert str(tgt) == 'fff.o', str(tgt)
        assert len(tgt.sources) == 1, map(str, tgt.sources)
        assert str(tgt.sources[0]) == 'fff.c', map(str, tgt.sources)

        tgt = b(env, source='ggg.x.c')
        assert str(tgt) == 'ggg.x.o', str(tgt)
        assert len(tgt.sources) == 1, map(str, tgt.sources)
        assert str(tgt.sources[0]) == 'ggg.x.c', map(str, tgt.sources)

        tgt = b(env, source=['h0.c', 'h1.c'])
        assert str(tgt) == 'h0.o', str(tgt)
        assert len(tgt.sources) == 2,  map(str, tgt.sources)
        assert str(tgt.sources[0]) == 'h0.c', map(str, tgt.sources)
        assert str(tgt.sources[1]) == 'h1.c', map(str, tgt.sources)

        w = b(env, target='i0.w', source=['i0.x'])
        y = b(env, target='i1.y', source=['i1.z'])
        tgt = b(env, source=[w, y])
        assert str(tgt) == 'i0.o', str(tgt)
        assert len(tgt.sources) == 2, map(str, tgt.sources)
        assert str(tgt.sources[0]) == 'i0.w', map(str, tgt.sources)
        assert str(tgt.sources[1]) == 'i1.y', map(str, tgt.sources)


if __name__ == "__main__":
    suite = unittest.makeSuite(BuilderTestCase, 'test_')
    if not unittest.TextTestRunner().run(suite).wasSuccessful():
        sys.exit(1)

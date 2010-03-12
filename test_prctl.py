# python-pctrl -- python interface to the prctl function
# (c)2010 Dennis Kaarsemaker <dennis@kaarsemaker.net
# See COPYING for licensing details

import distutils.util
import glob
import os
import re
import signal
import sys
import subprocess
import unittest

curdir = os.path.dirname(__file__)
builddir = os.path.join(curdir, 'build', 'lib.%s-%s' % (distutils.util.get_platform(), sys.version[0:3]))

# Always run from the builddir
if not os.path.exists(builddir) or \
   not os.path.exists(os.path.join(builddir, 'prctl.py')) or \
   not os.path.exists(os.path.join(builddir, '_prctl.so')) or \
   os.path.getmtime(os.path.join(curdir, 'prctl.py')) > os.path.getmtime(os.path.join(builddir, 'prctl.py')) or \
   os.path.getmtime(os.path.join(curdir, '_prctlmodule.c')) > os.path.getmtime(os.path.join(builddir, '_prctl.so')):
     print >>sys.stderr, "Please build the extension first, using ./setup.py build"
     sys.exit(1)
sys.path.insert(0, builddir)

import prctl
import _prctl

class PrctlTest(unittest.TestCase):
    # There are architecture specific tests
    arch = os.uname()[4]
    # prctl behaviour differs when root, so you should test as root and non-root
    am_root = os.geteuid() == 0

    def test_constants(self):
        """Test whether copying of constants works"""
        self.assertEquals(prctl.ENDIAN_LITTLE, _prctl.PR_ENDIAN_LITTLE)
        self.assertEquals(prctl.SECURE_NOROOT, _prctl.SECURE_NOROOT)
        self.assertEquals(prctl.CAP_SYS_ADMIN, _prctl.CAP_SYS_ADMIN)
        self.assertRaises(AttributeError, getattr, prctl, 'PR_ENDIAN_LITTLE')
        self.assertRaises(AttributeError, getattr, prctl, 'PR_CAPBSET_READ')
        self.assertRaises(AttributeError, getattr, prctl, 'CAPBSET_READ')

    def test_capbset(self):
        """Test the get_capbset/set_capbset functions"""
        self.assertEquals(prctl.capbset_read(prctl.CAP_NET_ADMIN), True)
        if self.am_root:
            self.assertEqual(prctl.capbset_drop(prctl.CAP_NET_ADMIN), None)
            self.assertEqual(prctl.capbset_read(prctl.CAP_NET_ADMIN), False)
        else:
            self.assertRaises(OSError, prctl.capbset_drop, prctl.CAP_SYS_ADMIN)
        self.assertRaises(ValueError, prctl.capbset_read, 999)

    def test_capbset_object(self):
        """Test manipulation of the capability bounding set via the capbset object"""
        self.assertEqual(prctl.capbset.sys_admin, True)
        if self.am_root:
            prctl.capbset.sys_admin = False
            self.assertEqual(prctl.capbset.sys_admin, False)
        else:
            def set_false():
                prctl.capbset.sys_admin = False
            self.assertRaises(OSError, set_false)
        def set_true():
            prctl.capbset.sys_admin = True
        self.assertRaises(ValueError, set_true)
        def unknown_attr():
            prctl.capbset.foo = 1
        self.assertRaises(AttributeError, unknown_attr)

    def test_dumpable(self):
        """Test manipulation of the dumpable flag"""
        prctl.set_dumpable(True)
        self.assertEqual(prctl.get_dumpable(), True)
        prctl.set_dumpable(False)
        self.assertEqual(prctl.get_dumpable(), False)
        self.assertRaises(TypeError, prctl.get_dumpable, "42")

    def test_endian(self):
        """Test manipulation of the endianness setting"""
        if self.arch == 'powerpc':
            # FIXME untested
            prctl.set_endian(prctl.ENDIAN_BIG)
            self.assertEqual(prctl.get_endian(), prctl.ENDIAN_BIG)
            prctl.set_endian(prctl.ENDIAN_LITTLE)
            self.assertEqual(prctl.get_endian(), prctl.ENDIAN_LITTLE)
            self.assertRaises(ValueError, prctl.set_endian, 999)
        else:
            self.assertRaises(OSError, prctl.get_endian)
            self.assertRaises(OSError, prctl.set_endian)
    
    def test_fpemu(self):
        """Test manipulation of the fpemu setting"""
        if self.arch == 'ia64':
            # FIXME - untested
            prctl.set_fpemu(prctl.FPEMU_SIGFPE)
            self.assertEqual(prctl.get_fpemu(), prctl.FPEMU_SIGFPE)
            prctl.set_fpemu(prctl.FPEMU_NOPRINT)
            self.assertEqual(prctl.get_fpemu(), prctl.FPEMU_NOPRINT)
            self.assertRaises(ValueError, prctl.set_fpexc, 999)
        else:
            self.assertRaises(OSError, prctl.get_fpemu)
            self.assertRaises(OSError, prctl.set_fpemu, prctl.FPEMU_SIGFPE)

    def test_fpexc(self):
        """Test manipulation of the fpexc setting"""
        if self.arch == 'powerpc':
            # FIXME - untested
            prctl.set_fpexc(prctl.FP_EXC_SW_ENABLE)
            self.assertEqual(prctl.get_fpexc() & prctl.PR_FP_EXC_SW_ENABLE, prctl.PR_FP_EXC_SW_ENABLE)
            self.assertRaises(ValueError, prctl.set_fpexc, 999)
        else:
            self.assertRaises(OSError, prctl.get_fpexc)
            self.assertRaises(OSError, prctl.set_fpexc)

    def test_keepcaps(self):
        """Test manipulation of the keepcaps setting"""
        prctl.set_keepcaps(True)
        self.assertEqual(prctl.get_keepcaps(), True)
        prctl.set_keepcaps(False)
        self.assertEqual(prctl.get_keepcaps(), False)

    def test_name(self):
        """Test setting the process name"""
        name = prctl.get_name().swapcase() * 16
        prctl.set_name(name)
        self.assertEqual(prctl.get_name(), name[:15])

    def test_proctitle(self):
        """Test setting the prcess title, including too long titles"""
        title = "This is a test!"
        prctl.set_proctitle(title)
        ps_output = subprocess.Popen(['ps', '-f', '-p', '%d' % os.getpid()],
                                     stdout=subprocess.PIPE).communicate()[0]
        self.assertTrue(ps_output.strip().endswith(title))
        # This should not segfault but truncate
        title2 = "And this is a test too!"
        prctl.set_proctitle(title2)
        ps_output = subprocess.Popen(['ps', '-f', '-p', '%d' % os.getpid()],
                                     stdout=subprocess.PIPE).communicate()[0]
        self.assertTrue(ps_output.strip().endswith(title2[:len(title)]))

    def test_pdeathsig(self):
        """Test manipulation of the pdeathsig setting"""
        self.assertRaises(ValueError, prctl.set_pdeathsig, 999)
        self.assertEqual(prctl.get_pdeathsig(), 0)
        prctl.set_pdeathsig(signal.SIGINT)
        self.assertEqual(prctl.get_pdeathsig(), signal.SIGINT)

    def test_seccomp(self):
        """Test manipulation of the seccomp setting"""
        self.assertEqual(prctl.get_seccomp(), False)
        result = os.fork()
        if result == 0:
            # In child
            prctl.set_seccomp(True)
            # This should kill ourselves
            open('/etc/resolv.conf')
            # If not, kill ourselves anyway
            sys.exit(0)
        else:
            pid, result = os.waitpid(result, 0)
            self.assertTrue(os.WIFSIGNALED(result))
            self.assertEqual(os.WTERMSIG(result), signal.SIGKILL)

    def test_securebits(self):
        """Test manipulation of the securebits flag"""
        self.assertEqual(prctl.get_securebits(), 0)
        if os.geteuid() == 0:
            prctl.set_securebits(1 << prctl.SECURE_KEEP_CAPS)
            self.assertEqual(prctl.get_securebits(), 1 << prctl.SECURE_KEEP_CAPS)
        else:
            self.assertRaises(OSError, prctl.set_securebits, 1 << prctl.SECURE_KEEP_CAPS)
    
    def test_securebits_obj(self):
        """Test manipulation of the securebits via the securebits object"""
        self.assertEqual(prctl.securebits.noroot, False)
        if os.geteuid() == 0:
            prctl.securebits.noroot = True
            self.assertEqual(prctl.securebits.noroot, True)
            prctl.securebits.noroot_locked = True
            def set_false():
                prctl.securebits.noroot = False
            self.assertRaises(OSError, set_false)
        else:
            def set_true():
                prctl.securebits.noroot = True
            self.assertRaises(OSError, set_true)

    def test_timing(self):
        """Test manipulation of the timing setting"""
        self.assertRaises(OSError, prctl.set_timing, prctl.TIMING_TIMESTAMP);
        self.assertEquals(prctl.get_timing(), prctl.TIMING_STATISTICAL)
        prctl.set_timing(prctl.TIMING_STATISTICAL)
        self.assertEquals(prctl.get_timing(), prctl.TIMING_STATISTICAL)

    def test_tsc(self):
        """Test manipulation of the timestamp counter flag"""
        if re.match('i.86', self.arch):
            prctl.set_tsc(prctl.TSC_SIGSEGV)
            self.assertEquals(prctl.get_tsc(), prctl.TSC_SIGSEGV)
            prctl.set_tsc(prctl.TSC_ENABLE)
            self.assertEquals(prctl.get_tsc(), prctl.TSC_ENABLE)
        else:
            # FIXME untested
            self.assertRaises(OSError, prctl.get_tsc)
            self.assertRaises(OSError, prctl.set_tsc, prctl.TSC_ENABLE)

    def test_unalign(self):
        """Test manipulation of the unalogned access setting"""
        if self.arch in ('ia64', 'parisc', 'powerpc', 'alpha'):
            # FIXME untested
            prctl.set_unalign(prctl.UNALIGN_NOPRINT)
            self.assertEquals(prctl.get_unalign(), prctl.UNALIGN_NOPRINT)
            prctl.set_unalign(prctl.UNALIGN_SIGBUS)
            self.assertEquals(prctl.get_unalign(), prctl.UNALIGN_SIGBUS)
        else:
            self.assertRaises(OSError, prctl.get_unalign)
            self.assertRaises(OSError, prctl.set_unalign, prctl.UNALIGN_NOPRINT)

if __name__ == '__main__':
    unittest.main()

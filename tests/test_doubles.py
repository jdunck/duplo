from __future__ import absolute_import

from mock import patch
import sys, unittest

from duplo import doubles

class ContextTests(unittest.TestCase):
    def setUp(self):
        self.c = doubles.Context(lambda: 0)

    def test_pop_on_empty(self):
        self.assertRaises(doubles.EmptyContext, self.c.pop)

    def test_push_allows_pop(self):
        self.c.push()
        self.c.pop()

    def test_set_get(self):
        self.c['x'] = 1
        self.assertEquals(self.c['x'], 1)

    def test_update_allows_get(self):
        self.assertEquals(self.c['a'], 0)
        self.c.update({'a': 2})
        self.assertEquals(self.c['a'], 2)

    def test_update_does_not_push(self):
        self.assertEquals(self.c.depth, 1)
        self.c.update({'a': 1})
        self.assertEquals(self.c.depth, 1)

    def test_set_shadows_existing(self):
        self.c['a'] = 1
        self.c.push()
        self.c['a'] = 2
        self.assertEquals(self.c['a'], 2)
        self.c.pop()
        self.assertEquals(self.c['a'], 1)

    def test_get_depends_on_stack(self):
        self.c['a'] = 1
        self.c.push()
        self.c['b'] = 2
        self.assertEquals(self.c['a'], 1)
        self.c.pop()
        self.assertEquals(self.c['a'], 1)
        self.assertEquals(self.c['b'], 0)

    def test_keys_respect_frames(self):
        self.c['a'] = 1
        self.c.push()
        self.c['b'] = 1
        self.assertEquals(sorted(self.c.keys()), ['a', 'b'])
        self.c.pop()
        self.assertEquals(self.c.keys(), ['a'])

    def test_items(self):
        self.c['b'] = 1
        self.c['c'] = 2
        actual = sorted(self.c.items())
        self.assertEquals(actual, [('b', 1), ('c', 2)])


    def test_default_value(self):
        self.assertEquals(self.c['a'], 0)

class ExampleDoubler(doubles.DoublerBase):
    def apply(self):
        pass
    def unapply(self):
        pass

class NotDoubler(object):
    name = 'x'

class DoubleManagerTests(unittest.TestCase):
    def setUp(self):
        self.dm = doubles.DoubleManager()

    def test_takes_registration(self):
        self.dm.register_double(ExampleDoubler('example'))

    def test_register_only_doubles(self):
        with self.assertRaises(doubles.MissingDouble):
            self.dm.register_double(NotDoubler())

    def test_duplicate_registration(self):
        self.dm.register_double(ExampleDoubler('example'))
        with self.assertRaises(doubles.DuplicateRegistration):
            self.dm.register_double(ExampleDoubler('example'))

    def test_missing_double_exception(self):
        with self.assertRaises(doubles.MissingDouble):
            self.dm.apply_doubles(include=['nope'])

    def test_apply_returns_applied(self):
        self.dm.register_double(ExampleDoubler('example'))
        self.dm.register_double(ExampleDoubler('example2'))
        self.assertEqual(self.dm.apply_doubles(['example']), ['example'])

    def test_exclude_resolution(self):
        self.dm.register_double(ExampleDoubler('example'))
        self.dm.register_double(ExampleDoubler('example2'))
        self.dm.register_double(ExampleDoubler('example3'))
        self.dm.apply_doubles(exclude='example3')
        self.assertEquals(sorted(self.dm.applied), ['example', 'example2'])

    def test_include_resolution(self):
        self.dm.register_double(ExampleDoubler('example'))
        self.dm.register_double(ExampleDoubler('example2'))
        self.dm.register_double(ExampleDoubler('example3'))
        self.dm.apply_doubles(include='example3')
        self.assertEquals(sorted(self.dm.applied), ['example3'])

    def test_implied_resolution(self):
        self.dm.register_double(ExampleDoubler('example'))
        self.dm.register_double(ExampleDoubler('example2'))
        self.dm.register_double(ExampleDoubler('example3'))
        self.dm.apply_doubles()
        self.assertEquals(sorted(self.dm.applied), ['example', 'example2', 'example3'])

    def test_only_include_xor_exclude(self):
        self.dm.register_double(ExampleDoubler('example'))
        self.dm.register_double(ExampleDoubler('example2'))
        with self.assertRaises(ValueError):
            self.dm.apply_doubles(include='example', exclude='example2')

    @patch.object(ExampleDoubler, 'apply')
    def test_applied(self, mock_apply):
        self.dm.register_double(ExampleDoubler('example'))
        self.assertEquals(self.dm.applied, [])
        self.dm.apply_doubles(['example'])
        self.assertEquals(self.dm.applied, ['example'])

    @patch.object(ExampleDoubler, 'unapply')
    @patch.object(ExampleDoubler, 'apply')
    def test_takes_action(self, mock_apply, mock_unapply):
        self.dm.register_double(ExampleDoubler('example'))

        self.assertEquals(mock_apply.call_count, 0)
        self.assertEquals(mock_unapply.call_count, 0)

        self.dm.apply_doubles(['example'])

        self.assertEquals(mock_apply.call_count, 1)
        self.assertEquals(mock_unapply.call_count, 0)

        self.dm.unapply_doubles(['example'])

        self.assertEquals(mock_apply.call_count, 1)
        self.assertEquals(mock_unapply.call_count, 1)

        self.dm.apply_doubles(['example'])

        self.assertEquals(mock_apply.call_count, 2)
        self.assertEquals(mock_unapply.call_count, 1)

        self.dm.revert()

        self.assertEquals(mock_apply.call_count, 2)
        self.assertEquals(mock_unapply.call_count, 2)

    def test_returns_only_newly_applied(self):
        self.dm.register_double(ExampleDoubler('example'))
        self.dm.register_double(ExampleDoubler('example2'))
        self.assertEqual(sorted(self.dm.apply_doubles(['example', 'example2'])),
                         ['example', 'example2'])
        self.assertEqual(self.dm.apply_doubles(['example2']), [])

    def test_unapply(self):
        self.dm.register_double(ExampleDoubler('example'))
        self.dm.register_double(ExampleDoubler('example2'))
        self.assertEquals(self.dm.apply_doubles(['example']), ['example'])
        self.assertEquals(self.dm.unapply_doubles(['example']), ['example'])
        self.assertEquals(self.dm.unapply_doubles(['example']), [])

    def test_revert(self):
        self.dm.register_double(ExampleDoubler('example'))
        self.assertEquals(self.dm.apply_doubles(['example']), ['example'])
        self.assertEquals(self.dm.unapply_doubles(['example']), ['example'])
        self.assertFalse(self.dm.is_applied('example'))
        self.dm.revert()
        self.assertTrue(self.dm.is_applied('example'))
        self.dm.revert()
        self.assertFalse(self.dm.is_applied('example'))

    def test_empty_revert(self):
        with self.assertRaises(doubles.UnappliedDouble):
            self.dm.revert()

class ContextBasedTests(unittest.TestCase):
    def setUp(self):
        self.dm = doubles.DoubleManager()
        self.dm.register_double(ExampleDoubler('example'))
        self.dm.register_double(ExampleDoubler('example2'))

    def test_nested_application(self):
        self.assertFalse(self.dm.is_applied('example'))
        self.assertFalse(self.dm.is_applied('example2'))

        with doubles.applied(self.dm, 'example'):
            self.assertTrue(self.dm.is_applied('example'))
            self.assertFalse(self.dm.is_applied('example2'))

            with doubles.applied(self.dm, 'example2'):
                self.assertTrue(self.dm.is_applied('example'))
                self.assertTrue(self.dm.is_applied('example2'))

            self.assertTrue(self.dm.is_applied('example'))
            self.assertFalse(self.dm.is_applied('example2'))

        self.assertFalse(self.dm.is_applied('example'))
        self.assertFalse(self.dm.is_applied('example2'))

    def test_nested_unapplication(self):
        self.assertFalse(self.dm.is_applied('example'))
        self.assertFalse(self.dm.is_applied('example2'))

        with doubles.applied(self.dm, 'example'):
            self.assertTrue(self.dm.is_applied('example'))
            self.assertFalse(self.dm.is_applied('example2'))

            with doubles.unapplied(self.dm, 'example'):
                self.assertFalse(self.dm.is_applied('example'))
                self.assertFalse(self.dm.is_applied('example2'))

            self.assertTrue(self.dm.is_applied('example'))
            self.assertFalse(self.dm.is_applied('example2'))

        self.assertFalse(self.dm.is_applied('example'))
        self.assertFalse(self.dm.is_applied('example2'))

thing_to_patch = 0
variant_value = object()

class ObjectPatchingDoubler(doubles.PatchingDoubler):
    def __init__(self, name):
        super(ObjectPatchingDoubler, self).__init__(name, 1, [__name__ + ':thing_to_patch'])

class MissingObjectPatchingDoubler(doubles.PatchingDoubler):
    def __init__(self, name):
        super(MissingObjectPatchingDoubler, self).__init__(name, 1, [__name__ + ':missing_thing_to_patch'])

class ModulePatchingDoubler(doubles.PatchingDoubler):
    def __init__(self, name):
        super(ModulePatchingDoubler, self).__init__(name, 1, ['a_fictitous_module'])

class LazyVariantPatchingDoubler(doubles.PatchingDoubler):
    def __init__(self, name):
        super(LazyVariantPatchingDoubler, self).__init__(name, __name__ + ':variant_value', [__name__+':thing_to_patch'])


class PatchingDoublerTests(unittest.TestCase):
    def setUp(self):
        global thing_to_patch
        thing_to_patch = 0
        self.opd = ObjectPatchingDoubler('opd')
        self.bad_opd = MissingObjectPatchingDoubler('bad_opd')
        self.mpd = ModulePatchingDoubler('mpd')
        self.lazy_pd = LazyVariantPatchingDoubler('lazy_pd')

    def test_one_target_required(self):
        with self.assertRaises(doubles.MissingPatchTarget):
            doubles.PatchingDoubler('test', 1, [])

    def test_targets_either_modules_or_objects(self):
        self.opd.apply()
        self.mpd.apply()
        self.assertTrue('a_fictitous_module' in sys.modules)
        self.assertEquals(thing_to_patch, 1)

        self.opd.unapply()
        self.mpd.unapply()

    def test_raises_for_bad_targets(self):
        with self.assertRaises(doubles.MissingPatchTarget):
            doubles.PatchingDoubler("bad_targets", __name__ + ':variant_value', [])

    def test_patches_object(self):
        self.assertEquals(thing_to_patch, 0)
        self.opd.apply()
        self.assertEquals(thing_to_patch, 1)
        self.opd.unapply()
        self.assertEquals(thing_to_patch, 0)

    def test_patching_missing_object_is_noisy(self):
        with self.assertRaises(doubles.MissingPatchTarget):
            self.bad_opd.apply()

    def test_patches_module(self):
        self.assertEquals(thing_to_patch, 0)
        self.mpd.apply()
        self.assertTrue('a_fictitous_module' in sys.modules)
        self.mpd.unapply()
        self.assertFalse('a_fictitous_module' in sys.modules)

    def test_remembers_original_object(self):
        self.opd.apply()
        self.assertEquals(self.opd.normals, [0])
        self.opd.unapply()
        self.assertEquals(self.opd.normals, [])

    def test_unbalanced_unapply(self):
        with self.assertRaises(doubles.UnexpectedUnapply):
            self.opd.unapply()

    def test_importable_string_variant(self):
        self.lazy_pd.apply()
        self.assertEquals(thing_to_patch, variant_value)
        self.lazy_pd.unapply()
        self.assertEquals(thing_to_patch, 0)

if __name__ == '__main__':
    unittest.main()
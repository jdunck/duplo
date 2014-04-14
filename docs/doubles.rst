Test Doubles
============

If you have tests that depend on some expensive subsystem, consider using `test doubles`_ like so:

One-time setup::

    from duplo import doubles
    mailing_list_doubler = doubles.PatchingDoubler(
        'mailing_list', 'mail.helpers:FakeMailingListManager',
        'mail.swappables:MailingListManager'
    )
    manager.register_double(mailing_list_doubler)

    shortener_doubler = doubles.PatchingDoubler(
        'url_shortener', 'core.utils.url_shortener:stub_shorten_url',
        'core.swappables:shorten_url'
    )
    manager.register_double(shortener_doubler)

    double_manager = doubles.DoubleManager()

Then, in tests::

    double_manager.apply_doubles(include=['url_shortener'])

*or*::

    with doubles.applied('url_shortener'):
         # stubbed shortener requests here
    # normal shortener requests here.

----

For external dependencies, tests generally benefit from having a fake implementation for unit tests of collaborating parts of the system, having a unit test comparing the real implementation with the fake one, and then using the real implementation for an integration test of the overall subsystem.

This can save dozens or hundreds of calls to external APIs.  You can be fairly sure that those APIs work as documented, and that any bugs encounter will be in your code, not theirs.  By implementing fakes, assuring parity, and then preferring fakes in unrelated tests, debugging is simplified (because you have full inspection of the local fake) and your tests will be faster and more stable (by avoiding network calls and depending on 3rd-party services for testing purposes).

If you have used mock.py (particularly mock.patch), you know that finding and maintaining the locations of patches for code under test can be a headache.  This module makes it relatively easy to create test doubles which are applied when you want and unapplied when you want.

Package-specific jargon:

  * A Context, which keeps track of matched calls to apply_doubles (or unapply_doubles) and revert, which restores the previous state of the system.
  * A Doubler, an abstract class which provides interface for the work of swapping out the needed components with test doubles.
  * A DoubleManager, which responds to requests for specific application (or reversion) of double swaps.
  * A pair of context managers (the python feature, not to be confused with Context, above) to manage short-lived swaps under specific test conditions.
  * An "applied" double is in place for all other code (the dependent code does not need to change in order to use and benefit from the double).  An "unapplied" double means the normal, non-double implementation is in place.
  * A "target" is an object to be patched, while a "variant" is the object swapped in when the double is applied.  Target and variant strings are expected to be "path.to.module:attribute" if patching an attribute, or "path.to.module" if patching an entire module.
  * "Resolution" is the logic of mapping variant or target strings to their related objects.rgets) to their related objects.

duplo.doubles presently includes just one concrete Doubler implementation (PatchingDoubler), which replaces a module or attribute with a double via monkey-patching.  This Doubler strategy is roughly equivalent to mock.patch, except that multiple patch targets can be managed in the Doubler instance, while all tests refer to the set of patches using an shorthand alias, e.g. "mailing_list" above.  It's a simple, pragmatic approach that will work in most cases.  Alternative Doubler implementations might rely on import hooks or on searching the object space.  Those approaches might be architecturally purer, but they would also require a good bit more work to bear fruit.  (If you have ideas about how to do double application management, I'd like to hear them.)  A PatchingDoubler targets the one or more aliases. When a PatchingDoubler is unapplied, the original object is set back.

If you currently use mock.patch, you might find that management is eased by making a PatchingDoubler whose variant is the mock and whose targets are the set of all paths the target object is aliased. Once you've got that working, you can use the rule of thumb that whenever you write an import statement for something you'd like to double, you should also add a new target to the Doubler.

To illustrate the general problem of patching a double, consider a module, ham.py, which has an attrbute `spam = []`.  Then a third module, eggs.py which does `from ham import spam` has a reference to spam, but this is addressable as eggs.spam, not ham.spam, by other modules.  eggs.spam is an alias of ham.spam.  If we then want to replace ham.spam, we must find all aliases and replace those as well, otherwise the abstraction of the replacement is lost.

To simplify the application of doubles, you may prefer to designate a place in the tree from which all doubled components will be imported.  For example, if you import swappable objects from a "swappables" module, where the rest of your codebase references that module rather than making new object aliases, then patching can target just the one swappables attribute, easing Doubler instance configuration.

Target and variant strings are expected to be "path.to.module:attribute" if patching an attribute, or "path.to.module" if patching an entire module.

Given this toolset, if you find the need for a test double, the steps to use one are:

 * implement the needed double, which must be polymorphic with the normal implementation.
 * define and register an instance of a PatchingDoubler. This can be usefully done in as setUpClass method of a unittest.TestCase or a py.test fixture.
 * decide whether this double should be applied by default and, if so, call double_manager.apply_doubles(include=[...]) in setUp and double_manager.revert() in tearDown.
 * change tests as needed when you prefer the normal or the variant as defined in the PatchingDoubler by using the "unapplied" and "applied" context managers within test methods.

.. _`test doubles`: http://www.martinfowler.com/bliki/TestDouble.html
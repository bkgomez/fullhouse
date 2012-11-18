from django.conf import settings
from django.contrib.sites.models import RequestSite
from django.contrib.sites.models import Site

from registration import signals
from registration.forms import RegistrationForm
from registration.models import RegistrationProfile
from registration.backends.default import DefaultBackend

from fullhouse.dashboard.models import UserProfile
from emailusernames.forms import EmailUserCreationForm


class FullhouseBackend(DefaultBackend):
    """
    A custom registration backend which follows a simple workflow:

    1. User signs up, inactive account is created.

    2. Email is sent to user with activation link.

    3. User clicks activation link, account is now active.

    Using this backend requires that

    * ``registration`` be listed in the ``INSTALLED_APPS`` setting
      (since this backend makes use of models defined in this
      application).

    * The setting ``ACCOUNT_ACTIVATION_DAYS`` be supplied, specifying
      (as an integer) the number of days from registration during
      which a user may activate their account (after that period
      expires, activation will be disallowed).

    * The creation of the templates
      ``registration/activation_email_subject.txt`` and
      ``registration/activation_email.txt``, which will be used for
      the activation email. See the notes for this backends
      ``register`` method for details regarding these templates.

    Additionally, registration can be temporarily closed by adding the
    setting ``REGISTRATION_OPEN`` and setting it to
    ``False``. Omitting this setting, or setting it to ``True``, will
    be interpreted as meaning that registration is currently open and
    permitted.

    Internally, this is accomplished via storing an activation key in
    an instance of ``registration.models.RegistrationProfile``. See
    that model and its custom manager for full documentation of its
    fields and supported operations.

    """
    def register(self, request, **kwargs):
        """
        Given an email address and password, register a new
        user account, which will initially be inactive.

        Along with the new ``User`` object, a new
        ``registration.models.RegistrationProfile`` will be created,
        tied to that ``User``, containing the activation key which
        will be used for this account.

        An email will be sent to the supplied email address; this
        email should contain an activation link. The email will be
        rendered using two templates. See the documentation for
        ``RegistrationProfile.send_activation_email()`` for
        information about these templates and the contexts provided to
        them.

        After the ``User`` and ``RegistrationProfile`` are created and
        the activation email is sent, the signal
        ``registration.signals.user_registered`` will be sent, with
        the new ``User`` as the keyword argument ``user`` and the
        class of this backend as the sender.

        """
        email, password = (kwargs['email'], kwargs['password1'])

        #TODO: get site data from settings
        if Site._meta.installed:
            site = Site.objects.get_current()
        else:
            site = RequestSite(request)
        # pass the email as the username. The actual creation of
        # the User object is managed by emailusernames. Under
        # the hood, it patches the default User object to return
        # the email for User.username, but in the database it
        # actually saves the username as a hash of the email.
        #
        # This works correctly provided we use EmailUserCreationForm
        # (or any similar form) which checks for duplicate emails in
        # its validation method.
        new_user = RegistrationProfile.objects.create_inactive_user(
            email, email, password, site
        )
        # Here create fullhouse custom UserProfile object
        user_profile = UserProfile.objects.create(user=new_user)

        signals.user_registered.send(sender=self.__class__,
                                     user=new_user,
                                     request=request)
        return new_user

    def get_form_class(self, request):
        """
        Return the default form class used for user registration.

        """
        return EmailUserCreationForm

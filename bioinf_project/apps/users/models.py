from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, Permission, Group, PermissionsMixin
from django.core.urlresolvers import reverse
from django.db.models.signals import post_save, post_delete

from tags.models import Tag
# Create your models here.


###  atrributes of a user model:
# username, first_name, last_name, e-mail, password
# groups, user_permissions, is_staff, is_active, is_superuser
# last_login, date_joined
### methods:
# get_username, is_anonyous, is_authenticated, get_full_name, get_short_name
# set_password, check_password, has_perm, has_perms, email_user

class UserManager(BaseUserManager):
    def create_user(self, email, password=None):
        """
        Creates and saves a User with the given email, name and password.
        """
        if not email:
            raise ValueError('Users must have an email address')

        user = self.model(
            email=self.normalize_email(email), 
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password):
        """
        Creates and saves a superuser with the given email, name and password.
        """
        user = self.create_user(email, 
            password=password,
        )
        user.is_admin = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

class User(AbstractBaseUser,PermissionsMixin):
    # user manager
    objects = UserManager()
    # required information 
    email = models.EmailField(verbose_name="email address", db_index=True, max_length=255, unique=True)
    # required to identify the user. 
    USERNAME_FIELD = 'email'
    
    #user_permission = models.ManyToManyField(Permission, null=True, blank=True)
    #group = models.ManyToManyField(Group, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    
    def get_full_name(self):
        # The user is identified by their email address
        return self.email

    def get_short_name(self):
        # The user is identified by their email address
        return self.email

    def __str__(self):              # __unicode__ on Python 2
        return self.email


    @property
    def is_staff(self):
        "Is the user a member of staff?"
        # Simplest possible answer: All admins are staff
        return self.is_admin

class UserProfile(models.Model):

    user = models.OneToOneField("User", related_name="user_profile")
    name = models.CharField(verbose_name="user name", max_length=255, null=False, blank=False)
    location = models.CharField(verbose_name="location", max_length=255, blank=True)
    website = models.URLField(blank=True)
    biography = models.TextField(blank=True)
    portrait = models.ImageField(upload_to="user_photo", null=True, blank=True)
    reputation = models.IntegerField(default=1)
    following = models.ManyToManyField('self',blank=True, related_name = "follower")
    watched_tags = models.ManyToManyField(Tag, blank=True, related_name = "user")

    def __unicode__(self):
        return self.user.email

    @staticmethod
    def create_user_profile(sender, instance, **kwargs):
        new_user = instance
        new_user_profile = UserProfile.objects.get_or_create(user=new_user, name="user-"+str(new_user.id))

    def get_absolute_url(self):
        return reverse("users:profile-view", kwargs={'pk':self.pk})
    
post_save.connect(UserProfile.create_user_profile, sender=User)

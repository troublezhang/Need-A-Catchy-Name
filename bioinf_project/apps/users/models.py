from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, Permission, Group, PermissionsMixin
from django.core.urlresolvers import reverse
from django.db.models.signals import post_save, post_delete, pre_delete, pre_save
from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib.contenttypes.models import ContentType

from tags.models import Tag
from utils.models import Vote, Comment
from posts.models import ReplyPost
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
    email_verified = models.BooleanField(verbose_name="email verified?", default=False)
    is_moderator = models.BooleanField(verbose_name="moderator", default=False)

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

    def __str__(self):# __unicode__ on Python 2
        return self.email

    def questions(self):
        return self.mainpost_set.filter(type=0)
        
    def discussions(self):
        return self.mainpost_set.filter(type=1)
        
    def blogs(self):
        return self.mainpost_set.filter(type=2)
    
    @property
    def is_staff(self):
        "Is the user a member of staff?"
        # Simplest possible answer: All admins are staff
        return self.is_admin

    @property
    def unread_notification_count(self):
        return self.notifications.filter(unread = True).count()
    
    def exceed_new_post_limit(self):
        post_past_24h = self.mainpost_set.filter(created__gte = timezone.now() - timedelta(hours=24))
        if post_past_24h.count() >= 10: # will elaborate on this limit in the future. 
            return True
        else:
            return False
            
    def exceed_new_answer_limit(self):
        answer_past_24h = self.replypost_set.filter(created__gte = timezone.now() - timedelta(hours=24), mainpost__type = 0)
        if answer_past_24h.count() >= 10:
            return True
        else: 
            return False
            
    def exceed_new_reply_limit(self):
        answer_past_hour = self.replypost_set.filter(created__gte = timezone.now() - timedelta(hours=1))
        if answer_past_hour.count() >= 10:
            return True
        else: 
            return False
            
    def exceed_new_comment_limit(self):
        comment_past_24h = self.comment_set.filter(created__gte = timezone.now() - timedelta(hours=24))
        if comment_past_24h.count() >= 20:
            return True
        else: 
            return False        
        
    def exceed_vote_limit(self):
        vote_past_24h = self.votes.filter(date__gte = timezone.now() - timedelta(hours=24))
        if vote_past_24h.count() >= 20:
            return True
        else:
            return False
        
def generate_image_path(instance, filename):
    return '/'.join(['user_portrait','user-'+str(instance.pk), filename])
        
class UserProfile(models.Model):
    # user profile information. 
    user = models.OneToOneField("User", related_name="user_profile")
    name = models.CharField(verbose_name="user name", max_length=255, null=False, blank=False)
    location = models.CharField(verbose_name="location", max_length=255, blank=True)
    website = models.URLField(blank=True)
    biography = models.TextField(blank=True)
    portrait = models.ImageField(upload_to=generate_image_path, null=True, blank=True)
    reputation = models.IntegerField(default=1)
    following = models.ManyToManyField('UserProfile',blank=True, related_name = "followers")
    watched_tags = models.ManyToManyField(Tag, blank=True, related_name = "user")
    date_joined = models.DateTimeField(verbose_name="date joined", editable=False)
    last_activity = models.DateTimeField(verbose_name="last activity", null=True,blank=True)
    
    IMMEDIATE, DAILY, WEEKLY, NONE = range(4)
    BOOKMARK_CHOICES = [(IMMEDIATE, 'update immediately'), (DAILY, 'update daily'), (WEEKLY, 'update weekly'), (NONE, 'No e-mail update')]
    bookmark_update = models.IntegerField(verbose_name = 'Bookmark e-mail', choices = BOOKMARK_CHOICES, default=IMMEDIATE)
    
    def save(self, *args, **kwargs):
        if not self.date_joined: 
            self.date_joined = timezone.now()
        super(UserProfile, self).save()
            
    def __unicode__(self):
        return self.user.email
    @property
    def follower(self):
        return UserProfile.objects.filter(following__pk = self.pk)
    
    @staticmethod
    def create_user_profile(sender, instance, **kwargs):
        new_user = instance
        new_user_profile, created = UserProfile.objects.get_or_create(user=new_user)
        if created == True: 
            new_user_profile.name = 'user-'+str(new_user_profile.id)
            new_user_profile.save()

    @staticmethod
    def reputation_from_vote(sender, instance, **kwargs):
        content_type = instance.content_type
        obj_id = instance.object_id
        obj = content_type.get_object_for_this_type(pk=obj_id)
        choice = instance.choice
        if hasattr(obj, 'author'): 
            user_profile = obj.author.user_profile
            user_profile.reputation += choice
            user_profile.save()
    
    @staticmethod
    def reputation_rollback_from_vote(sender, instance, **kwargs):
        content_type = instance.content_type
        obj_id = instance.object_id
        obj = content_type.get_object_for_this_type(pk=obj_id)
        choice = instance.choice
        if hasattr(obj, 'author'): 
            user_profile = obj.author.user_profile
            user_profile.reputation -= choice
            user_profile.save()    
        
    def get_absolute_url(self):
        return reverse("users:profile-view", kwargs={'pk':self.pk})
    
post_save.connect(UserProfile.create_user_profile, sender=User)
post_save.connect(UserProfile.reputation_from_vote, sender=Vote)
pre_delete.connect(UserProfile.reputation_rollback_from_vote, sender=Vote)

class Notification(models.Model):
    # notification for items that the user bookmarked
    user = models.ForeignKey("User", related_name="notifications")
    message = models.TextField(blank=True)
    created = models.DateTimeField()
    unread = models.BooleanField(default=True)
    POSTS, WIKI, TAG, USER = range(4)
    TYPE_CHOICES = [(POSTS, 'posts'), (WIKI, 'wiki'), (TAG, 'tag'), (USER, 'user')]
    type = models.IntegerField(choices=TYPE_CHOICES)
    
    def __unicode__(self):
        return u'%s, %s' %(self.user.user_profile.name, self.message)
    
    @staticmethod
    def message_from_posts(sender, instance, **kwargs):
        if instance.pk: #if the instance exists.
            return 
        link = reverse('posts:post-detail', kwargs={'pk':instance.mainpost.id})
        if instance.mainpost.type == 0:
            message = "New answer added to "
        elif instance.mainpost.type == 1: 
            message = "New reply added to "
        message += "post <a href='"+link+"#"+str(instance.pk)+"'>" +instance.mainpost.title+"</a>"
        bookmarks = instance.mainpost.post_bookmark.all()
        if bookmarks.count() < 1: 
            return # exit
        for bookmark in bookmarks:
            user = bookmark.reader
            try: 
                notification = Notification.objects.get(message=message, type=0, user=user)
            except Notification.DoesNotExist:
                notification = Notification(user=user, message=message, created=timezone.now(), unread=True, type=0)
            else:
                notification.created = timezone.now()
                notification.unread = True
            notification.save()

    @staticmethod
    def message_from_post_comments(sender, instance, **kwargs):
        if instance.pk: #if the instance exists, exit. 
            return 
        
        if instance.content_type == ContentType.objects.get(app_label="posts", model="mainpost"):
            bookmarks = instance.content_object.post_bookmark.all()
            mainpost = instance.content_object
        elif instance.content_type == ContentType.objects.get(app_label="posts", model="replypost"):
            bookmarks = instance.content_object.mainpost.post_bookmark.all()
            mainpost = instance.content_object.mainpost
        else: # if the comments are not made on mainpost or reply post.
            return
        if bookmarks.count() < 1:
            return # if there is no bookmark, exit. 
        message = "New comment on post <a href='" + reverse('posts:post-detail', kwargs={'pk':mainpost.id}) + "'>" + mainpost.title +"</a>"
        for bookmark in bookmarks:
            user = bookmark.reader
            try: 
                notification = Notification.objects.get(message=message, type=0, user=user)
            except Notification.DoesNotExist:
                notification = Notification(user=user, message=message, created=timezone.now(), unread=True, type=0)
            else:
                notification.created = timezone.now()
                notification.unread = True
            notification.save()
       
    class Meta:
        unique_together = ('user', 'message', 'type')
 
pre_save.connect(Notification.message_from_posts, sender=ReplyPost)
pre_save.connect(Notification.message_from_post_comments, sender=Comment)

#class Timeline(models.Model):
    # timeline of the user.   
   

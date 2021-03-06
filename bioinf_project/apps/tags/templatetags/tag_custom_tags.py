from django import template
from django.http import HttpResponse
from tags.models import Tag
register = template.Library()


#list the tags according to their hierarchical structure.

@register.inclusion_tag("tags/templatetags/show_tags_children.html")
def show_tag_children(tag):
    tag_children_list = tag.children.all()
    return {'tag_list': tag_children_list}


@register.inclusion_tag("tags/templatetags/show_omics_tag_children.html")
def show_omics_tag_children(tag):
    tag_children_list = tag.children.all()
    return {'tag_list': tag_children_list}


@register.inclusion_tag("tags/templatetags/show_tag_ancestor.html")
def show_tag_ancestor(tag):
     try:
        tag.parent
     # if there is no parent to this tag.
     except AttributeError:
        return
     return {'tag': tag.parent}
#    else:

@register.inclusion_tag("tags/templatetags/display_tag.html")
def display_tag(tag):
    return {'tag': tag}

@register.inclusion_tag("tags/templatetags/display_tag_list.html")
def display_tag_list(tag_list):
    return {'tag_list': tag_list}

    
@register.inclusion_tag("tags/templatetags/tag_answers_for_user.html")
def tag_answers_for_user(usertag):
    return {'tag':usertag.tag,'user':usertag.user,'count':usertag.answer_count}

    
@register.inclusion_tag("tags/templatetags/user_answers_for_tag.html")
def user_answers_for_tag(usertag):
    return {'tag':usertag.tag, 'user':usertag.user,'count':usertag.answer_count}
    
@register.inclusion_tag("tags/templatetags/workflow_tab.html")
def display_workflow_tab(tag):
    return {'tag':tag}
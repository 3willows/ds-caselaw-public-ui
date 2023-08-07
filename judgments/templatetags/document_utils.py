from django import template

register = template.Library()


@register.filter
def get_title_to_display_in_html(document_title, document_noun):
    if document_noun == "press summary":
        return document_title.removeprefix("Press Summary of ")
    return document_title

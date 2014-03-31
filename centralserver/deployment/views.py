import datetime
import os
from annoying.decorators import render_to
from collections_local_copy import Counter, OrderedDict
from datetime import timedelta  # this is OK; central server code can be 2.7+

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Sum, Max, Count, F, Q, Min

from kalite.facility.models import Facility
from kalite.settings import LOG as logging
from kalite.shared.decorators import require_authorized_admin


@require_authorized_admin
@render_to("deployment/cms.html")
def show_deployment_cms(request):

    logins_with_facilities = Facility.objects \
        .filter(signed_by__devicemetadata__is_trusted=False) \
        .values( \
            "name", "address", \
            "latitude", "longitude", \
            "contact_email", "contact_name", \
            "user_count",
            "signed_by__devicezone__zone__id", \
            "signed_by__devicezone__zone__organization__users__email", \
            "signed_by__devicezone__zone__organization__users__first_name",
            "signed_by__devicezone__zone__organization__users__last_name",
            "signed_by__devicezone__zone__organization__name",)
        #.extra (select={ \
        #    "facility_name": "name", \
        #    "zone_id": "signed_by__devicezone__zone__id", \
        #    "email": "signed_by__devicezone__zone__organization__users__email", \
        #    "org_name": "signed_by__devicezone__zone__organization__name", })

    def paginate_users(user_list, per_page=25, page=1):
        """
        Create pagination for users
        """
        if not user_list:
            users = []
            page_urls = {}

        else:
            #Create a Django Pagintor from QuerySet
            paginator = Paginator(user_list, per_page)
            try:
                #Try to render the page with the passed 'page' number
                users = paginator.page(page)
                #Call pages_to_show function that selects a subset of pages to link to
                listed_pages = pages_to_show(paginator, page)
            except PageNotAnInteger:
                #If not a proper page number, render page 1
                users = paginator.page(1)
                #Call pages_to_show function that selects a subset of pages to link to
                listed_pages = pages_to_show(paginator, 1)
            except EmptyPage:
                #If past the end of the page range, render last page
                users = paginator.page(paginator.num_pages)
                #Call pages_to_show function that selects a subset of pages to link to
                listed_pages = pages_to_show(paginator, paginator.num_pages)

        if users:
            #Generate URLs for pagination links
            if not users.has_previous():
                previous_page_url = ""
            else:
                #If there are pages before the current page, generate a link for 'previous page'
                prevGETParam = request.GET.copy()
                prevGETParam["page"] = users.previous_page_number()
                previous_page_url = "?" + prevGETParam.urlencode()

            if not users.has_next():
                next_page_url = ""
            else:
                #If there are pages after the current page, generate a link for 'next page'
                nextGETParam = request.GET.copy()
                nextGETParam["page"] = users.next_page_number()
                next_page_url = "?" + nextGETParam.urlencode()

            page_urls = {"next_page": next_page_url, "prev_page": previous_page_url}

            if listed_pages:
                #Generate URLs for other linked to pages
                for listed_page in listed_pages:
                    if listed_page != -1:
                        GETParam = request.GET.copy()
                        GETParam["page"] = listed_page
                        page_urls.update({listed_page: "?" + GETParam.urlencode()})
                users.listed_pages = listed_pages
                users.num_listed_pages = len(listed_pages)

        return users, page_urls

    user_pages, page_urls = paginate_users(logins_with_facilities, page=int(request.GET.get("page", 1)), per_page=25)

    return {
        "user_pages": user_pages,
        "page_urls": page_urls,
    }



def pages_to_show(paginator, page, pages_wanted=None, max_pages_wanted=9):
    """
    Function to select first two pages, last two pages and pages around currently selected page
    to show in pagination bar.
    """
    page = int(page)

    #Set precedence for displaying each page on the navigation bar.
    page_precedence_order = [page,1,paginator.num_pages,page+1,page-1,page+2,page-2,2,paginator.num_pages-1]

    if pages_wanted is None:
        pages_wanted = []

    #Allow for arbitrary pages wanted to be set via optional argument
    pages_wanted = set(pages_wanted) or set(page_precedence_order[:max_pages_wanted])

    #Calculate which pages actually exist
    pages_to_show = set(paginator.page_range).intersection(pages_wanted)
    pages_to_show = sorted(pages_to_show)

    #Find gaps larger than 1 in pages_to_show, indicating that a range of pages has been skipped here
    skip_pages = [ x[1] for x in zip(pages_to_show[:-1],
                                     pages_to_show[1:])
                   if (x[1] - x[0] != 1) ]

    #Add -1 to stand in for skipped pages which can then be rendered as an ellipsis.
    for i in skip_pages:
        pages_to_show.insert(pages_to_show.index(i), -1)

    return pages_to_show

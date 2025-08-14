# synergy_data/context_processors.py
from .models import SiteViewCounter

def view_counter(request):
    # get_or_create ensures we only ever have one counter object.
    # It tries to get the counter with ID=1, and if it doesn't exist, it creates it.
    counter, created = SiteViewCounter.objects.get_or_create(id=1)
    
    # Increment the count on every request and save it to the database
    counter.count += 1
    counter.save()
    
    # Return the count in a dictionary. This makes 'total_views' available in all templates.
    return {'total_views': counter.count}
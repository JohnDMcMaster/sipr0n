# Migration: adding collection (user) to files

add user "auser" => although really its collection

Updated core tools:
* simapper
* sipager

To run the migration:
* Stop all services
* auser_page.py: munge urls on the /archive wiki pages
  * NOTE: this uncovered a significant number of consistency errors that were fixed
* auser_map2unk.py: seed the new scheme in /map by marking everything un-attributed
* auser_map_annotate.py: try to more systematically assign copyrights
  * scrape copyright.txt and match to .html copyright strings
  * Find a wiki page that links there
  * See if they agree
* map_regenerate.py: try to regenerate all /map files to fix old issues

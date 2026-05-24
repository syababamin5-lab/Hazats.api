import sys

code = """
class SiteConfigUpdate(BaseModel):
    include_exclude: Optional[str] = None
    itinerary: Optional[str] = None

@app.get("/admin/config/site")
def get_site_config(db: Session = Depends(get_db)):
    config = db.query(models.SiteConfig).first()
    if not config:
        config = models.SiteConfig(include_exclude="", itinerary="")
        db.add(config)
        db.commit()
        db.refresh(config)
    return config

@app.put("/admin/config/site")
def update_site_config(item: SiteConfigUpdate, db: Session = Depends(get_db), admin: models.User = Depends(admin_required)):
    config = db.query(models.SiteConfig).first()
    if not config:
        config = models.SiteConfig(include_exclude=item.include_exclude, itinerary=item.itinerary)
        db.add(config)
    else:
        if item.include_exclude is not None:
            config.include_exclude = item.include_exclude
        if item.itinerary is not None:
            config.itinerary = item.itinerary
    db.commit()
    db.refresh(config)
    return config
"""

with open("main.py", "a", encoding="utf-8") as f:
    f.write(code)

from django.contrib import admin
from .models import LTIConsumer, OptionProperty, OptionList, PropertyName, Configuration, LTIUserProfile

# Register your models here.

class LTIConsumerAdmin(admin.ModelAdmin):
  readonly_fields = ('secret',)
  list_display = ('id', 'name', 'concat_secret')
  list_display_links = ('id', 'concat_secret')
  list_editable = ('name',)

  def concat_secret(self, instance):
    return instance.concat_secret()
  concat_secret.short_description = 'secret'

admin.site.register(LTIConsumer, LTIConsumerAdmin)
admin.site.register(LTIUserProfile)

class OptionPropertyInlineAdmin(admin.TabularInline):
  model = OptionProperty
  extra = 1

class OptionListInlineAdmin(admin.TabularInline):
  model = OptionList
  extra = 1
  show_change_link = True
  inlines = (OptionPropertyInlineAdmin,)

class OptionListAdmin(admin.ModelAdmin):
  list_display = ('name', 'config', 'parent', 'num_properties')
  inlines = (OptionPropertyInlineAdmin,OptionListInlineAdmin, )

class ConfigAdmin(admin.ModelAdmin):
  inlines = (OptionListInlineAdmin,)

class PropertyNameAdmin(admin.ModelAdmin):
  list_display = ('name', 'default', 'choices')
admin.site.register(Configuration, ConfigAdmin)
admin.site.register(OptionList, OptionListAdmin)
admin.site.register(PropertyName, PropertyNameAdmin)

from django.template import loader
from django.template.response import SimpleTemplateResponse

import jingo


# We monkeypatch SimpleTemplateResponse.rendered_content to use our jinja
# rendering pipeline (most of the time). The exception is the admin app, where
# we render their Django templates and pipe the result through jinja to render
# our page skeleton.
def rendered_content(self):
    template = self.template_name
    context_instance = self.resolve_context(self.context_data)
    request = context_instance['request']

    # Gross, let's figure out if we're in the admin.
    if self._current_app == 'admin':
        source = loader.render_to_string(template, context_instance)
        template = jingo.env.from_string(source)
        # This interferes with our media() helper.
        if 'media' in self.context_data:
            del self.context_data['media']

    # ``render_to_string`` only accepts a Template instance or a template name,
    # not a list.
    if isinstance(template, (list, tuple)):
        template = loader.select_template(template)
    return jingo.render_to_string(request, template, self.context_data)

SimpleTemplateResponse.rendered_content = property(rendered_content)

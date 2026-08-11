from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")
templates.env.globals["csrf_token"] = lambda request: getattr(request.state, "csrf_token", "")

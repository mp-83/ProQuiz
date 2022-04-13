def default_routes(config):
    # /new must come before /{uid} suffixed routes
    # because of route matching logic
    config.add_route("home", "/")
    config.add_route("login", "/login")
    config.add_route("logout", "/logout")
    config.add_route("new_question", "/question/new")
    config.add_route("get_question", "/question/{uid}")
    config.add_route("edit_question", "/question/edit/{uid}")
    config.add_route("list_matches", "/match/list")
    config.add_route("new_match", "/match/new")
    config.add_route("match_yaml_import", "/match/yaml_import")
    config.add_route("get_match", "/match/{uid}")
    config.add_route("edit_match", "/match/edit/{uid}")
    config.add_route("list_players", "/players")
    config.add_route("match_rankings", "/rankings")


def play_routes(config):
    # routes must come after others because of
    # the route matching logic
    config.add_route("start", "/start")
    config.add_route("next", "/next")
    config.add_route("code", "/code")
    config.add_route("sign", "/sign")
    config.add_route("land", "/{match_uhash}")


def includeme(config):
    config.include(default_routes)
    config.include(play_routes, route_prefix="/play")
    config.scan("codechallenge.endpoints.login")
    config.scan("codechallenge.endpoints.match")
    config.scan("codechallenge.endpoints.question")
    config.scan("codechallenge.endpoints.play")
    config.scan("codechallenge.endpoints.user")
    config.scan("codechallenge.endpoints.ranking")

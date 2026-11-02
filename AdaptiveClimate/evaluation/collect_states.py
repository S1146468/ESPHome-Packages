"""Compatibility entrypoint for sustained read-only collection; see COLLECTION.md."""
import json
import urllib.request


def snapshot(base,token,entities):
    request=urllib.request.Request(base.rstrip('/')+'/api/states',headers={'Authorization':'Bearer '+token})
    with urllib.request.urlopen(request,timeout=8) as response:
        states=json.load(response)
    return [s for s in states if s['entity_id'] in entities]


def main():
    from continuous_collection import main as sustained_main
    return sustained_main()


if __name__=='__main__':
    raise SystemExit(main())

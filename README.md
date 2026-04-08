# search-flights

A Claude Code skill that searches and compares flight prices using Google Flights data. Supports natural language input in Chinese and English.

## Install

```bash
git clone https://github.com/pierrezhiwei/search-flights.git
cd search-flights
bash setup.sh
ln -s "$(pwd)" ~/.claude/skills/search-flights
```

## Usage

In Claude Code, just describe what you need:

```
/search-flights 温哥华到北京，7月到8月，待25-45天，直飞
/search-flights 7月1号飞北京，30号回来
/search-flights 单程温哥华飞东京，8月25日
/search-flights Find cheapest YVR to PEK in July, about 2 weeks
/search-flights one way Vancouver to Tokyo, Aug 25
```

You can also be vague — Claude will ask follow-up questions:

```
/search-flights 帮我搜个暑假回国的机票
```

### Three Search Modes

| Mode | When | Example |
|---|---|---|
| Flexible date range | Compare prices across a window | "7月到8月之间，待2-4周" |
| Exact dates | Specific departure and return | "7月1号去，30号回" |
| One-way | No return needed | "单程飞东京，8月25日" |

### Supported Cities

The skill maps city names (Chinese/English) to IATA codes automatically:

Vancouver, Beijing, Shanghai, Toronto, Tokyo, Hong Kong, Taipei, Singapore, Seoul, Los Angeles, San Francisco, New York, London, Guangzhou, Shenzhen, Chengdu, Osaka, Bangkok, Kuala Lumpur, Sydney, Melbourne, Paris, Dubai, Seattle, Chicago, Calgary, Hangzhou, Nanjing, Xiamen, Chongqing, Wuhan, Xi'an, Kunming

You can also use IATA codes directly (e.g., YVR, PEK).

## Important Disclaimers

- **Data source**: This skill uses the [`fli`](https://github.com/nicklaros/fli) library, an **unofficial** reverse-engineered Google Flights API.
- **Price accuracy**: Prices are approximate and may differ from what you see on Google Flights. Always verify on the booking site before purchasing.
- **Availability**: Google may change their API at any time, which could break this skill without notice.
- **Not for commercial use**: This is a personal productivity tool. Do not use it for commercial flight booking services.

## Roadmap

- [ ] Multi-passenger support (adults, children, infants)
- [ ] Cabin class selection (business, first)
- [ ] Budget filter (max price)
- [ ] Multi-airport city search (e.g., Beijing PEK + PKX)
- [ ] Currency selection
- [ ] Additional data sources (Amadeus, Skyscanner)

## Development

```bash
# Run tests (no API calls, pure unit tests)
.venv/bin/python -m pytest tests/ -v
```

## License

MIT

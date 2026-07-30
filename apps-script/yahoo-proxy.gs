function doGet(event) {
  const callback = String(event.parameter.callback || "").trim();
  if (!/^[A-Za-z_$][A-Za-z0-9_$]{0,80}$/.test(callback)) {
    return ContentService.createTextOutput(
      JSON.stringify({
        chart: {
          result: null,
          error: { description: "Invalid callback" },
        },
      }),
    ).setMimeType(ContentService.MimeType.JSON);
  }

  const symbols = String(event.parameter.symbols || "")
    .split(",")
    .map((value) => value.trim().toUpperCase())
    .filter(Boolean);
  if (symbols.length) {
    return fetchBatch_(callback, symbols);
  }

  const symbol = String(event.parameter.symbol || "")
    .trim()
    .toUpperCase();

  if (!/^[A-Z0-9.^=-]{1,15}$/.test(symbol)) {
    return jsonpResponse_(callback, {
      chart: {
        result: null,
        error: { description: "Invalid ticker symbol" },
      },
    });
  }

  const cache = CacheService.getScriptCache();
  const cacheKey = `yahoo-history-${symbol}`;
  const cached = cache.get(cacheKey);
  if (cached) {
    return jsonpTextResponse_(callback, cached);
  }

  const startUnix = Math.floor(
    new Date("2020-01-01T00:00:00Z").getTime() / 1000,
  );
  const endUnix = Math.floor(Date.now() / 1000) + 86400;
  const yahooSymbol = encodeURIComponent(symbol.replace(".", "-"));
  const url =
    `https://query1.finance.yahoo.com/v8/finance/chart/${yahooSymbol}` +
    `?period1=${startUnix}&period2=${endUnix}&interval=1d` +
    "&events=history&includeAdjustedClose=true";

  try {
    const response = UrlFetchApp.fetch(url, {
      muteHttpExceptions: true,
      headers: {
        Accept: "application/json",
        "User-Agent": "Mozilla/5.0 MomentumConsole/1.0",
      },
    });
    const status = response.getResponseCode();
    const body = response.getContentText();

    if (status < 200 || status >= 300) {
      return jsonpResponse_(callback, {
        chart: {
          result: null,
          error: {
            description: `${symbol}: Yahoo Finance request failed (${status})`,
          },
        },
      });
    }

    if (body.length < 90000) {
      cache.put(cacheKey, body, 21600);
    }
    return jsonpTextResponse_(callback, body);
  } catch (error) {
    return jsonpResponse_(callback, {
      chart: {
        result: null,
        error: {
          description:
            error instanceof Error
              ? error.message
              : `${symbol}: market data request failed`,
        },
      },
    });
  }
}

function fetchBatch_(callback, requestedSymbols) {
  const symbols = Array.from(
    new Set(
      requestedSymbols.filter((symbol) =>
        /^[A-Z0-9.^=-]{1,15}$/.test(symbol),
      ),
    ),
  ).slice(0, 60);

  if (!symbols.length) {
    return jsonpResponse_(callback, {
      histories: {},
      errors: ["No valid ticker symbols"],
    });
  }

  const endUnix = Math.floor(Date.now() / 1000) + 86400;
  const startUnix = endUnix - 86400 * 550;
  const requests = symbols.map((symbol) => {
    const yahooSymbol = encodeURIComponent(symbol.replace(".", "-"));
    return {
      url:
        `https://query1.finance.yahoo.com/v8/finance/chart/${yahooSymbol}` +
        `?period1=${startUnix}&period2=${endUnix}&interval=1d` +
        "&events=history&includeAdjustedClose=true",
      method: "get",
      muteHttpExceptions: true,
      headers: {
        Accept: "application/json",
        "User-Agent": "Mozilla/5.0 MomentumConsole/1.0",
      },
    };
  });

  try {
    const responses = UrlFetchApp.fetchAll(requests);
    const histories = {};
    const errors = [];

    responses.forEach((response, index) => {
      const symbol = symbols[index];
      const status = response.getResponseCode();
      if (status < 200 || status >= 300) {
        errors.push(`${symbol}: Yahoo Finance request failed (${status})`);
        return;
      }

      try {
        const body = JSON.parse(response.getContentText());
        const result = body.chart &&
          body.chart.result &&
          body.chart.result[0];
        const timestamps = (result && result.timestamp) || [];
        const indicators = (result && result.indicators) || {};
        const adjusted =
          indicators.adjclose &&
          indicators.adjclose[0] &&
          indicators.adjclose[0].adjclose;
        const quoted =
          indicators.quote &&
          indicators.quote[0] &&
          indicators.quote[0].close;
        const closes = adjusted || quoted || [];

        histories[symbol] = timestamps
          .map((timestamp, pointIndex) => {
            const close = closes[pointIndex];
            if (
              typeof close !== "number" ||
              !isFinite(close) ||
              close <= 0
            ) {
              return null;
            }
            return {
              date: new Date(timestamp * 1000)
                .toISOString()
                .slice(0, 10),
              close,
            };
          })
          .filter(Boolean);
      } catch (error) {
        errors.push(`${symbol}: invalid Yahoo Finance response`);
      }
    });

    return jsonpResponse_(callback, { histories, errors });
  } catch (error) {
    return jsonpResponse_(callback, {
      histories: {},
      errors: [
        error instanceof Error
          ? error.message
          : "Yahoo Finance batch request failed",
      ],
    });
  }
}

function jsonpResponse_(callback, value) {
  return jsonpTextResponse_(callback, JSON.stringify(value));
}

function jsonpTextResponse_(callback, jsonText) {
  return ContentService.createTextOutput(
    `${callback}(${jsonText});`,
  ).setMimeType(ContentService.MimeType.JAVASCRIPT);
}

function authorizeYahooProxy() {
  const response = UrlFetchApp.fetch(
    "https://query1.finance.yahoo.com/v8/finance/chart/QQQ?range=5d&interval=1d",
    {
      muteHttpExceptions: true,
      headers: {
        Accept: "application/json",
        "User-Agent": "Mozilla/5.0 MomentumConsole/1.0",
      },
    },
  );
  console.log(`Yahoo Finance authorization check: ${response.getResponseCode()}`);
}

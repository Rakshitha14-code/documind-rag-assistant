import streamlit as st

def apply_custom_theme():
    """Injects the DocuMind Adobe-inspired design system CSS."""
    custom_css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600&family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap');

    :root {
        --dm-primary: #B42332;
        --dm-primary-hover: #961B28;
        --dm-bg-main: #FFF9F0;
        --dm-blush: #F7E8E5;
        --dm-panel-white: #FFFFFF;
        --dm-text-primary: #252525;
        --dm-text-secondary: #706B68;
        --dm-border: #E9DED7;
        --dm-success: #287D55;
        --dm-error: #B42332;
        --dm-shadow-subtle: 0 4px 16px rgba(180, 35, 50, 0.06);
        --dm-shadow-card: 0 2px 10px rgba(37, 37, 37, 0.04);
        --dm-radius: 12px;
    }

    /* Overall App Background & Font */
    html, body, [data-testid="stAppViewContainer"] {
        background-color: var(--dm-bg-main) !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        color: var(--dm-text-primary) !important;
    }

    [data-testid="stHeader"] {
        background-color: transparent !important;
    }

    /* Heading Typography */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Outfit', sans-serif !important;
        color: var(--dm-text-primary) !important;
        font-weight: 600 !important;
        letter-spacing: -0.02em;
        overflow-wrap: break-word !important;
        word-break: break-word !important;
        max-width: 100% !important;
    }

    /* Main Content Layout & Responsive Width Constraints */
    html, body {
        overflow-x: hidden !important;
        max-width: 100vw !important;
    }

    [data-testid="stAppViewContainer"] {
        overflow-x: hidden !important;
    }

    .main, [data-testid="stMain"] {
        background-color: var(--dm-bg-main) !important;
        overflow-x: hidden !important;
        max-width: 100% !important;
    }

    .main .block-container {
        max-width: 1400px !important;
        width: 100% !important;
        padding-top: 1.5rem !important;
        padding-bottom: 2.5rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        margin: 0 auto !important;
        box-sizing: border-box !important;
        overflow-x: hidden !important;
    }

    /* Prevent clipping on metric cards and dashboard columns */
    [data-testid="stHorizontalBlock"] {
        width: 100% !important;
        box-sizing: border-box !important;
        align-items: stretch !important;
        gap: 1rem !important;
    }

    [data-testid="column"] {
        min-width: 0 !important;
        box-sizing: border-box !important;
    }

    /* Sidebar Layout & Creamy-White Background (#FFF9F0) */
    section[data-testid="stSidebar"],
    section[data-testid="stSidebar"] > div,
    [data-testid="stSidebarContent"],
    [data-testid="stSidebarUserContent"],
    [data-testid="stSidebarNav"] {
        background-color: #FFF9F0 !important;
        color: #252525 !important;
    }

    section[data-testid="stSidebar"] {
        width: 270px !important;
        min-width: 260px !important;
        max-width: 280px !important;
        border-right: 1px solid var(--dm-border) !important;
    }

    [data-testid="stSidebarContent"] {
        padding: 1.25rem 1rem !important;
        overflow-x: hidden !important;
    }

    [data-testid="stSidebar"] hr {
        border-color: var(--dm-border) !important;
        margin: 0.75rem 0 !important;
    }

    /* Ensure all text inside the sidebar defaults to dark charcoal */
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] div,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: #252525;
    }

    /* Sidebar Navigation Container */
    [data-testid="stSidebar"] [data-testid="stRadio"] {
        margin-top: 0 !important;
        margin-bottom: 0.4rem !important;
        width: 100% !important;
    }

    /* Completely hide any widget label for the radio group */
    [data-testid="stSidebar"] [data-testid="stRadio"] > label,
    [data-testid="stSidebar"] [data-testid="stRadio"] [data-testid="stWidgetLabel"],
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        width: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        position: absolute !important;
        pointer-events: none !important;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] {
        display: flex !important;
        flex-direction: column !important;
        gap: 4px !important;
        width: 100% !important;
    }

    /* Hide the default radio circle indicator dot and native input without hiding text */
    [data-testid="stSidebar"] [data-testid="stRadio"] input[type="radio"],
    [data-testid="stSidebar"] [data-testid="stRadioOption"] > div > div:first-child:not([data-testid="stMarkdownContainer"]),
    [data-testid="stSidebar"] [data-testid="stRadioOption"] div:has(+ [data-testid="stMarkdownContainer"]),
    [data-testid="stSidebar"] [data-testid="stRadioOption"] [class*="e1dm8mpf4"] {
        display: none !important;
        visibility: hidden !important;
        width: 0 !important;
        height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        opacity: 0 !important;
        position: absolute !important;
        pointer-events: none !important;
    }

    /* Style each navigation item label as a clickable pill/tab */
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label,
    [data-testid="stSidebar"] [data-testid="stRadioOption"] {
        display: flex !important;
        align-items: center !important;
        padding: 0.55rem 0.85rem !important;
        border-radius: 8px !important;
        cursor: pointer !important;
        transition: all 0.15s ease !important;
        background-color: transparent !important;
        margin: 0 !important;
        width: 100% !important;
        box-sizing: border-box !important;
        border: 1px solid transparent !important;
    }

    /* Ensure text container is always fully visible */
    [data-testid="stSidebar"] [data-testid="stRadioOption"] > div,
    [data-testid="stSidebar"] [data-testid="stRadioOption"] [data-testid="stMarkdownContainer"],
    [data-testid="stSidebar"] [data-testid="stRadioOption"] p {
        display: flex !important;
        align-items: center !important;
        visibility: visible !important;
        opacity: 1 !important;
        width: 100% !important;
    }

    /* Default Navigation Item: Dark charcoal text (#252525) */
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label [data-testid="stMarkdownContainer"] p,
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label p,
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label span {
        color: #252525 !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.88rem !important;
        font-weight: 500 !important;
        line-height: 1.4 !important;
        margin: 0 !important;
        text-decoration: none !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }

    /* Vector Navigation Icons via ::before */
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label p::before {
        content: "" !important;
        display: inline-block !important;
        min-width: 18px !important;
        width: 18px !important;
        height: 18px !important;
        vertical-align: -3px !important;
        margin-right: 0.65rem !important;
        background-color: #706B68 !important;
        -webkit-mask-size: contain !important;
        mask-size: contain !important;
        -webkit-mask-repeat: no-repeat !important;
        mask-repeat: no-repeat !important;
        -webkit-mask-position: center !important;
        mask-position: center !important;
        transition: background-color 0.15s ease !important;
        flex-shrink: 0 !important;
    }

    /* Base64 SVG Icons precisely mapped by radio value attribute and child index */
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input[value="Dashboard"]) p::before,
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > div:nth-child(1) label p::before {
        -webkit-mask-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZD0iTTMgMTNoOFYzSDN2MTB6bTAgOGg4di02SDN2NnptMTAgMGg4VjExaC04djEwem0wLTE4djZoOFYzaC04eiIvPjwvc3ZnPg==") !important;
        mask-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZD0iTTMgMTNoOFYzSDN2MTB6bTAgOGg4di02SDN2NnptMTAgMGg4VjExaC04djEwem0wLTE4djZoOFYzaC04eiIvPjwvc3ZnPg==") !important;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input[value="My Documents"]) p::before,
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > div:nth-child(2) label p::before {
        -webkit-mask-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZD0iTTEwIDRINGMtMS4xIDAtMS45OS45LTEuOTkgMkwyIDE4YzAgMS4xLjkgMiAyIDJoMTZjMS4xIDAgMi0uOSAyLTJWOGMwLTEuMS0uOS0yLTItMmgtOGwtMi0yeiIvPjwvc3ZnPg==") !important;
        mask-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZD0iTTEwIDRINGMtMS4xIDAtMS45OS45LTEuOTkgMkwyIDE4YzAgMS4xLjkgMiAyIDJoMTZjMS4xIDAgMi0uOSAyLTJWOGMwLTEuMS0uOS0yLTItMmgtOGwtMi0yeiIvPjwvc3ZnPg==") !important;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input[value="Chat with Documents"]) p::before,
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > div:nth-child(3) label p::before {
        -webkit-mask-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZD0iTTIwIDJINGMtMS4xIDAtMS45OS45LTEuOTkgMkwyIDIybDQtNGgxNGMxLjEgMCAyLS45IDItMlY0YzAtMS4xLS45LTItMi0yek02IDloMTJ2Mkg2Vjl6bTggNUg2di0yaDh2MnptNC02SDZWNmgxMnYyeiIvPjwvc3ZnPg==") !important;
        mask-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZD0iTTIwIDJINGMtMS4xIDAtMS45OS45LTEuOTkgMkwyIDIybDQtNGgxNGMxLjEgMCAyLS45IDItMlY0YzAtMS4xLS45LTItMi0yek02IDloMTJ2Mkg2Vjl6bTggNUg2di0yaDh2MnptNC02SDZWNmgxMnYyeiIvPjwvc3ZnPg==") !important;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input[value="Compare Documents"]) p::before,
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > div:nth-child(4) label p::before {
        -webkit-mask-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZD0iTTkuMDEgMTRIMnYyaDcuMDF2M0wxMyAxNWwtMy45OS00djN6bTUuOTgtMXYtM0gyMlY4aC03LjAxVjVMMTEgOWwzLjk5IDR6Ii8+PC9zdmc+") !important;
        mask-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZD0iTTkuMDEgMTRIMnYyaDcuMDF2M0wxMyAxNWwtMy45OS00djN6bTUuOTgtMXYtM0gyMlY4aC03LjAxVjVMMTEgOWwzLjk5IDR6Ii8+PC9zdmc+") !important;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input[value="Saved Notes"]) p::before,
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > div:nth-child(5) label p::before {
        -webkit-mask-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZD0iTTMgMTcuMjVWMjFoMy43NUwxNy44MSA5Ljk0bC0zLjc1LTMuNzVMMyAxNy4yNXpNMjAuNzEgNy4wNGMuMzktLjM5LjM5LTEuMDIgMC0xLjQxbC0yLjM0LTIuMzRjLS4zOS0uMzktMS4wMi0uMzktMS40MSAwbC0xLjgzIDEuODMgMy43NSAzLjc1IDEuODMtMS44M3oiLz48L3N2Zz4=") !important;
        mask-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZD0iTTMgMTcuMjVWMjFoMy43NUwxNy44MSA5Ljk0bC0zLjc1LTMuNzVMMyAxNy4yNXpNMjAuNzEgNy4wNGMuMzktLjM5LjM5LTEuMDIgMC0xLjQxbC0yLjM0LTIuMzRjLS4zOS0uMzktMS4wMi0uMzktMS40MSAwbC0xLjgzIDEuODMgMy43NSAzLjc1IDEuODMtMS44M3oiLz48L3N2Zz4=") !important;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input[value="Exports & Reports"]) p::before,
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > div:nth-child(6) label p::before {
        -webkit-mask-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZD0iTTE5IDNINWMtMS4xIDAtMiAuOS0yIDJ2MTRjMCAxLjEuOSAyIDIgMmgxNGMxLjEgMCAyLS45IDItMlY1YzAtMS4xLS45LTItMi0yem0tNSAxNEg3di0yaDd2MnptMy00SDd2LTJoMTB2MnptMC00SDdWN2gxMHYyeiIvPjwvc3ZnPg==") !important;
        mask-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZD0iTTE5IDNINWMtMS4xIDAtMiAuOS0yIDJ2MTRjMCAxLjEuOSAyIDIgMmgxNGMxLjEgMCAyLS45IDItMlY1YzAtMS4xLS45LTItMi0yem0tNSAxNEg3di0yaDd2MnptMy00SDd2LTJoMTB2MnptMC00SDdWN2gxMHYyeiIvPjwvc3ZnPg==") !important;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input[value="Settings"]) p::before,
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > div:nth-child(7) label p::before {
        -webkit-mask-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZD0iTTE5LjE0IDEyLjk0Yy4wNC0uMy4wNi0uNjEuMDYtLjk0IDAtLjMyLS4wMi0uNjQtLjA3LS45NGwyLjAzLTEuNThjLjE4LS4xNC4yMy0uNDEuMTItLjYxbC0xLjkyLTMuMzJjLS4xMi0uMjItLjM3LS4yOS0uNTktLjIybC0yLjM5Ljk2Yy0uNS0uMzgtMS4wMy0uNy0xLjYyLS45NGwtLjM2LTIuNTRjLS4wNC0uMjQtLjI0LS40MS0uNDgtLjQxaC0zLjg0Yy0uMjQgMC0uNDMuMTctLjQ3LjQxbC0uMzYgMi41NGMtLjU5LjI0LTEuMTMuNTctMS42Mi45NGwtMi4zOS0uOTZjLS4yMi0uMDgtLjQ3IDAtLjU5LjIyTDIuNzQgOC44N2MtLjEyLjIxLS4wOC40Ny4xMi42MWwyLjAzIDEuNThjLS4wNS4zLS4wOS42My0uMDkuOTRzLjAyLjY0LjA3Ljk0bC0yLjAzIDEuNThjLS4xOC4xNC0uMjMuNDEtLjEyLjYxbDEuOTIgMy4zMmMuMTIuMjIuMzcuMjkuNTkuMjJsMi4zOS0uOTZjLjUuMzggMS4wMy43IDEuNjIuOTRsLjM2IDIuNTRjLjA1LjI0LjI0LjQxLjQ4LjQxaDMuODRjLjI0IDAgLjQ0LS4xNy40Ny0uNDFsLjM2LTIuNTRjLjU5LS4yNCAxLjEzLS41NiAxLjYyLS45NGwyLjM5Ljk2Yy4yMi4wOC40NyAwIC41OS0uMjJsMS45Mi0zLjMyYy4xMi0uMjIuMDctLjQ3LS4xMi0uNjFsLTIuMDEtMS41OHpNMTIgMTUuNmMtMS45OCAwLTMuNi0xLjYyLTMuNi0zLjZzMS42Mi0zLjYgMy42LTMuNiAzLjYgMS42MiAzLjYgMy42LTEuNjIgMy42LTMuNiAzLjZ6Ii8+PC9zdmc+") !important;
        mask-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZD0iTTE5LjE0IDEyLjk0Yy4wNC0uMy4wNi0uNjEuMDYtLjk0IDAtLjMyLS4wMi0uNjQtLjA3LS45NGwyLjAzLTEuNThjLjE4LS4xNC4yMy0uNDEuMTItLjYxbC0xLjkyLTMuMzJjLS4xMi0uMjItLjM3LS4yOS0uNTktLjIybC0yLjM5Ljk2Yy0uNS0uMzgtMS4wMy0uNy0xLjYyLS45NGwtLjM2LTIuNTRjLS4wNC0uMjQtLjI0LS40MS0uNDgtLjQxaC0zLjg0Yy0uMjQgMC0uNDMuMTctLjQ3LjQxbC0uMzYgMi41NGMtLjU5LjI0LTEuMTMuNTctMS42Mi45NGwtMi4zOS0uOTZjLS4yMi0uMDgtLjQ3IDAtLjU5LjIyTDIuNzQgOC44N2MtLjEyLjIxLS4wOC40Ny4xMi42MWwyLjAzIDEuNThjLS4wNS4zLS4wOS42My0uMDkuOTRzLjAyLjY0LjA3Ljk0bC0yLjAzIDEuNThjLS4xOC4xNC0uMjMuNDEtLjEyLjYxbDEuOTIgMy4zMmMuMTIuMjIuMzcuMjkuNTkuMjJsMi4zOS0uOTZjLjUuMzggMS4wMy43IDEuNjIuOTRsLjM2IDIuNTRjLjA1LjI0LjI0LjQxLjQ4LjQxaDMuODRjLjI0IDAgLjQ0LS4xNy40Ny0uNDFsLjM2LTIuNTRjLjU5LS4yNCAxLjEzLS41NiAxLjYyLS45NGwyLjM5Ljk2Yy4yMi4wOC40NyAwIC41OS0uMjJsMS45Mi0zLjMyYy4xMi0uMjIuMDctLjQ3LS4xMi0uNjFsLTIuMDEtMS41OHpNMTIgMTUuNmMtMS45OCAwLTMuNi0xLjYyLTMuNi0zLjZzMS42Mi0zLjYgMy42LTMuNiAzLjYgMS42MiAzLjYgMy42LTEuNjIgMy42LTMuNiAzLjZ6Ii8+PC9zdmc+") !important;
    }

    /* Hover state: Subtle blush background (#F7E8E5) */
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label:hover {
        background-color: var(--dm-blush) !important;
        border-color: rgba(180, 35, 50, 0.2) !important;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label:hover *,
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label:hover p,
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label:hover span,
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label:hover div {
        color: var(--dm-primary) !important;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label:hover p::before {
        background-color: var(--dm-primary) !important;
    }

    /* Selected Navigation Item: Light blush background (#F7E8E5) */
    [data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"],
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked),
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > div[data-selected="true"] label {
        background-color: var(--dm-blush) !important;
        border: 1px solid rgba(180, 35, 50, 0.25) !important;
    }

    /* Selected Navigation Text: Deep red (#B42332) */
    [data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] p,
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) p,
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > div[data-selected="true"] p {
        color: var(--dm-primary) !important;
        font-weight: 600 !important;
    }

    /* Selected Navigation Icon: Deep red (#B42332) */
    [data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] p::before,
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) p::before,
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > div[data-selected="true"] p::before {
        background-color: var(--dm-primary) !important;
    }

    /* Sidebar Sign Out Button */
    [data-testid="stSidebar"] button[kind="secondary"],
    [data-testid="stSidebar"] .stButton > button {
        background-color: #FFFFFF !important;
        color: #252525 !important;
        border: 1px solid var(--dm-border) !important;
        border-radius: 8px !important;
        padding: 0.55rem 1rem !important;
        font-size: 0.88rem !important;
        font-weight: 600 !important;
        font-family: 'Outfit', sans-serif !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important;
        width: 100% !important;
    }

    [data-testid="stSidebar"] button[kind="secondary"]:hover,
    [data-testid="stSidebar"] .stButton > button:hover {
        background-color: var(--dm-blush) !important;
        border-color: var(--dm-primary) !important;
        color: var(--dm-primary) !important;
        transform: translateY(-1px);
        box-shadow: 0 3px 8px rgba(180, 35, 50, 0.15) !important;
    }

    /* Primary and Secondary Buttons in Main Content */
    .main button[kind="primary"], .main .stButton > button:not([kind="secondary"]) {
        background-color: var(--dm-primary) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.55rem 1.4rem !important;
        font-weight: 500 !important;
        font-family: 'Outfit', sans-serif !important;
        letter-spacing: 0.01em;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
        box-shadow: 0 2px 6px rgba(180, 35, 50, 0.2) !important;
    }

    .main button[kind="primary"]:hover, .main .stButton > button:not([kind="secondary"]):hover {
        background-color: var(--dm-primary-hover) !important;
        color: #FFFFFF !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(180, 35, 50, 0.3) !important;
    }

    .main button[kind="secondary"], .main .stButton > button[kind="secondary"] {
        background-color: var(--dm-panel-white) !important;
        color: var(--dm-text-primary) !important;
        border: 1px solid var(--dm-border) !important;
        border-radius: 8px !important;
        transition: all 0.2s ease !important;
    }

    .main button[kind="secondary"]:hover, .main .stButton > button[kind="secondary"]:hover {
        border-color: var(--dm-primary) !important;
        color: var(--dm-primary) !important;
        background-color: var(--dm-blush) !important;
    }

    /* Form Inputs */
    .stTextInput input, .stTextArea textarea, .stSelectbox [data-baseweb="select"] {
        background-color: var(--dm-panel-white) !important;
        border: 1px solid var(--dm-border) !important;
        border-radius: 8px !important;
        color: var(--dm-text-primary) !important;
        font-family: 'Inter', sans-serif !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }

    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: var(--dm-primary) !important;
        box-shadow: 0 0 0 2px rgba(180, 35, 50, 0.15) !important;
    }

    /* Metric Containers */
    [data-testid="stMetric"] {
        background: var(--dm-panel-white) !important;
        border: 1px solid var(--dm-border) !important;
        border-radius: var(--dm-radius) !important;
        padding: 1.15rem 1.35rem !important;
        box-shadow: var(--dm-shadow-card) !important;
        box-sizing: border-box !important;
        width: 100% !important;
        overflow: hidden !important;
    }

    [data-testid="stMetricLabel"] p {
        color: var(--dm-text-secondary) !important;
        font-size: 0.8rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        font-weight: 600 !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }

    [data-testid="stMetricValue"] div {
        color: var(--dm-primary) !important;
        font-family: 'Outfit', sans-serif !important;
        font-size: 1.85rem !important;
        font-weight: 700 !important;
        overflow-wrap: break-word !important;
    }

    @media (max-width: 992px) {
        .main .block-container {
            padding-left: 1.25rem !important;
            padding-right: 1.25rem !important;
            padding-top: 1.25rem !important;
        }
    }

    @media (max-width: 768px) {
        .main .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            padding-top: 1rem !important;
        }

        section[data-testid="stSidebar"] {
            width: 100% !important;
            max-width: 100% !important;
        }
    }

    /* Custom Cards and UI Containers */
    .dm-card {
        background-color: var(--dm-panel-white);
        border: 1px solid var(--dm-border);
        border-radius: var(--dm-radius);
        padding: 1.5rem;
        margin-bottom: 1.2rem;
        box-shadow: var(--dm-shadow-card);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        box-sizing: border-box !important;
        max-width: 100% !important;
        overflow: hidden !important;
    }

    .dm-card:hover {
        box-shadow: var(--dm-shadow-subtle);
    }

    .dm-card-accent {
        background-color: var(--dm-blush);
        border: 1px solid rgba(180, 35, 50, 0.2);
        border-radius: var(--dm-radius);
        padding: 1.4rem;
        margin-bottom: 1.2rem;
    }

    .dm-badge {
        display: inline-block;
        padding: 0.25rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.02em;
    }

    .dm-badge-red {
        background-color: var(--dm-blush);
        color: var(--dm-primary);
        border: 1px solid rgba(180, 35, 50, 0.2);
    }

    .dm-badge-green {
        background-color: #E6F4EA;
        color: var(--dm-success);
        border: 1px solid rgba(40, 125, 85, 0.2);
    }

    .dm-badge-gray {
        background-color: #F1ECE6;
        color: var(--dm-text-secondary);
        border: 1px solid var(--dm-border);
    }

    /* Citation Snippet Pill */
    .dm-citation {
        background: #FFFFFF;
        border-left: 3px solid var(--dm-primary);
        border-top: 1px solid var(--dm-border);
        border-right: 1px solid var(--dm-border);
        border-bottom: 1px solid var(--dm-border);
        border-radius: 0 8px 8px 0;
        padding: 0.85rem 1.1rem;
        margin: 0.7rem 0;
        font-size: 0.88rem;
        line-height: 1.5;
        color: var(--dm-text-primary);
    }

    .dm-citation-meta {
        color: var(--dm-primary);
        font-weight: 600;
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        margin-bottom: 0.35rem;
    }

    /* Centered Login Card & Layout */
    .dm-login-card {
        background-color: var(--dm-panel-white) !important;
        border: 1px solid var(--dm-border) !important;
        border-radius: 16px !important;
        padding: 2.25rem 2rem 1.85rem 2rem !important;
        box-shadow: 0 10px 25px -5px rgba(37, 37, 37, 0.05), 0 8px 10px -6px rgba(37, 37, 37, 0.03) !important;
    }


    /* Empty state styling */
    .dm-empty-state {
        text-align: center;
        padding: 3.5rem 1.5rem;
        background: var(--dm-panel-white);
        border: 2px dashed var(--dm-border);
        border-radius: var(--dm-radius);
        margin: 1.5rem 0;
    }

    .dm-empty-state h3 {
        margin-top: 1rem;
        margin-bottom: 0.4rem;
        color: var(--dm-text-primary);
    }

    .dm-empty-state p {
        color: var(--dm-text-secondary);
        max-width: 440px;
        margin: 0 auto 1.5rem auto;
        font-size: 0.95rem;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 1px solid var(--dm-border);
        padding-bottom: 4px;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0 !important;
        padding: 8px 20px !important;
        font-family: 'Outfit', sans-serif !important;
        font-weight: 500 !important;
        color: var(--dm-text-secondary) !important;
    }

    .stTabs [aria-selected="true"] {
        color: var(--dm-primary) !important;
        border-bottom: 2px solid var(--dm-primary) !important;
        background-color: transparent !important;
    }

    /* Chat bubble styling */
    .stChatMessage {
        background: var(--dm-panel-white) !important;
        border: 1px solid var(--dm-border) !important;
        border-radius: 12px !important;
        padding: 1rem !important;
        margin-bottom: 0.8rem !important;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.03) !important;
    }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)

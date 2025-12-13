<#
.SYNOPSIS
    Scrapes the Mizrahi-Tefahot deals page for new offers and sends them via a Telegram bot.
.DESCRIPTION
    This script periodically checks the Mizrahi-Tefahot "Hot Deals" page for new promotions.
    It keeps a record of all deals found in the last month to avoid sending duplicate notifications.

    To improve performance and avoid rate-limiting, it uses:
    1. A local cache for the webpage to minimize requests to the Mizrahi-Tefahot server.
    2. A timed delay between sending Telegram messages to respect the Telegram API's limits.
.EXAMPLE
    .\mizrahi.ps1
    Runs the script with the default configured parameters.
.EXAMPLE
    .\mizrahi.ps1 -BotToken "YOUR_TOKEN" -ChatID "YOUR_CHAT_ID"
    Runs the script using a specific Bot Token and Chat ID provided at runtime.
#>
param(
    [Parameter(HelpMessage = 'Your Telegram Bot API Token.')]
    [string]$BotToken = "5721971334:AAEjHCnU75z3rASopTHMbvlJnICdhq9jnUM",

    [Parameter(HelpMessage = 'The ID of the Telegram chat to send messages to.')]
    [string]$ChatID = "-899742789",

    [Parameter(HelpMessage = 'The file path to store the list of previously found deal URLs.')]
    [string]$LinksCsvPath = "C:\Users\eladz\links.csv",

    [Parameter(HelpMessage = 'The file path for caching the webpage response.')]
    [string]$CacheFilePath = "C:\Users\eladz\mizrahi_cache.clixml",

    [Parameter(HelpMessage = 'The number of hours to keep the webpage cache before refreshing.')]
    [int]$CacheHours = 1,

    [Parameter(HelpMessage = 'The delay in seconds between sending Telegram messages to avoid rate limits.')]
    [int]$ApiSleepSeconds = 2
)

#==============================================================================
# SETUP LOGGING
#==============================================================================

# All output will be logged to a file in the same directory as the script.
$logDate = Get-Date -Format 'yyyy-MM-dd'
# $PSScriptRoot is an automatic variable that contains the directory of the script.
$logFilePath = Join-Path -Path $PSScriptRoot -ChildPath "mizrahi_log_$logDate.log"

# Start logging. -Append will add to the file if the script is run multiple times a day.
Start-Transcript -Path $logFilePath -Append


# The main script logic is wrapped in a try/finally block to ensure logging is
# always stopped, even if an error occurs.
try {

    #==============================================================================
    # FUNCTIONS
    #==============================================================================

    function Send-TelegramMessage {
    <#
    .SYNOPSIS
        Sends a text message using the Telegram Bot API.
    #>
        param(
            [string]$Token,
            [string]$TargetChatID,
            [string]$Message
        )

        # Ensure TLS 1.2 is used for modern API security.
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

        try {
            $url = "https://api.telegram.org/bot$Token/sendMessage?chat_id=$TargetChatID&text=$Message"
            Invoke-RestMethod -Uri $url -Method Post -ErrorAction Stop
        }
        catch {
            # Provide a more detailed error if the request fails.
            $errorMessage = $_.ErrorDetails.Message | ConvertFrom-Json
            Write-Error "Failed to send Telegram message. API Response: $($errorMessage.description)"
        }
    }


    #==============================================================================
    # SCRIPT BODY
    #==============================================================================

    # --- 1. Load Webpage (from Cache or Web) ---

    $baseurl = "https://www.mizrahi-tefahot.co.il"
    $dealsUrl = $baseurl + "/hacartis/hot-deals/"
    $cacheDuration = New-TimeSpan -Hours $CacheHours
    $webpage = $null

    if (Test-Path $CacheFilePath) {
        $fileInfo = Get-Item $CacheFilePath
        if ((Get-Date) - $fileInfo.LastWriteTime -lt $cacheDuration) {
            try {
                Write-Host "Loading webpage from cache (valid for $CacheHours hour(s))."
                $webpage = Import-Clixml -Path $CacheFilePath
            } catch {
                Write-Warning "Cache file '$CacheFilePath' is corrupt. Fetching from web."
            }
        }
    }

    # If cache is old, invalid, or doesn't exist, fetch a fresh copy from the web.
    if (-not $webpage) {
        Write-Host "Fetching fresh webpage from $dealsUrl..."
        try {
            $webpage = Invoke-WebRequest -Uri $dealsUrl -ErrorAction Stop
            $webpage | Export-Clixml -Path $CacheFilePath
        } catch {
            Write-Error "Failed to fetch webpage: $($_.Exception.Message)"
            # Exit gracefully if the web request fails, as there's nothing to process.
            # The 'return' is inside the try block, so the 'finally' block below will still run.
            return 
        }
    }


    # --- 2. Process Deals ---

    $dealLinksOnPage = $webpage.Links | Where-Object { $_.class -match "hatavasearch" }

    # Load the list of deals found within the last month.
    $oneMonthAgo = (Get-Date).AddMonths(-1)
    $previouslySeenLinks = @()
    if (Test-Path $LinksCsvPath) {
        $previouslySeenLinks = Import-Csv $LinksCsvPath -ErrorAction SilentlyContinue
    }

    $recentLinks = if ($previouslySeenLinks) {
        $previouslySeenLinks | Where-Object { 
            $date = Get-Date -Date $_.date -ErrorAction SilentlyContinue
            $date -and ($date -ge $oneMonthAgo)
        } | Sort-Object -Property url -Unique
    } else {
        @()
    }

    $recentUrls = [System.Collections.Generic.List[string]]@($recentLinks.url)
    $newlyFoundLinkObjects = @()

    Write-Host "Found $($dealLinksOnPage.Count) links on the page. Comparing against $($recentUrls.Count) known links from the last month."

    foreach ($link in $dealLinksOnPage){
        $fullUrl = $baseurl + $link.href
        if ($recentUrls.Contains($fullUrl)){
            # This link is already known, do nothing.
        }
        else{
            Write-Host "New deal found: $($link.innerText.Trim())"
            
            Send-TelegramMessage -Token $BotToken -TargetChatID $ChatID -Message $fullUrl
            Start-Sleep -Seconds $ApiSleepSeconds

            $newlyFoundLinkObjects += [PSCustomObject]@{
                url  = $fullUrl
                date = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
            }
            # Add the URL to the current list to avoid sending duplicates found in the same run.
            $recentUrls.Add($fullUrl) 
        }
    }


    # --- 3. Save Updated Link History ---

    if ($newlyFoundLinkObjects.Count -gt 0) {
        Write-Host "Adding $($newlyFoundLinkObjects.Count) new links to the history."
        $updatedLinks = $recentLinks + $newlyFoundLinkObjects
        $updatedLinks | Select-Object url, date | Export-Csv -Path $LinksCsvPath -NoTypeInformation -Force
    } else {
        Write-Host "No new deals found."
    }

    Write-Host "Script finished."

}
finally {
    # This block will always run, ensuring that logging is stopped correctly.
    Stop-Transcript
}

# user scripts and claude live here; the GNOME session PATH lacks it
fish_add_path -g $HOME/.local/bin

if status is-interactive
    set -g fish_greeting
    # ${ct_label} colours
    set -g fish_color_normal c0caf5
    set -g fish_color_command 7aa2f7
    set -g fish_color_keyword 7dcfff
    set -g fish_color_quote 9ece6a
    set -g fish_color_redirection c0caf5
    set -g fish_color_end ff9e64
    set -g fish_color_error f7768e
    set -g fish_color_param 7dcfff
    set -g fish_color_comment 565f89
    set -g fish_color_selection --background=283457
    set -g fish_color_search_match --background=283457
    set -g fish_color_operator 9ece6a
    set -g fish_color_escape 7dcfff
    set -g fish_color_autosuggestion 565f89
    set -g fish_color_valid_path --underline
    set -g fish_pager_color_progress 565f89
    set -g fish_pager_color_prefix 7dcfff
    set -g fish_pager_color_completion c0caf5
    set -g fish_pager_color_description 565f89
    fastfetch
    starship init fish | source
    zoxide init fish | source
    fzf --fish | source

    set -gx FZF_DEFAULT_OPTS "--color=bg+:${ct_surface2},fg:${ct_text},fg+:${ct_text},hl:${ct_sky},hl+:${ct_sky},info:${ct_overlay1},prompt:${ct_accent},pointer:${ct_accent},marker:${ct_green},spinner:${ct_accent},header:${ct_yellow},border:${ct_overlay0},label:${ct_text},selected-bg:${ct_surface2}"

    alias ls 'eza --icons --group-directories-first'
    alias ll 'eza -l --icons --git --group-directories-first'
    alias la 'eza -la --icons --git --group-directories-first'
    alias lt 'eza --tree --level=2 --icons'
    alias cat 'bat --paging=never'
    alias top btop
end

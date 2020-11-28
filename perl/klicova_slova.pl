#!/usr/bin/perl

###########################################################
# by Jan Rychly                     
# 
# Simple key word extractor - analyzes a text file,
# finds its most frequently used words and prints them out
# from the most to the least frequent.
# It ignores words from '$ignore_path' if it exits and
# by default it ignores 2 or 1 letter words and shows only
# words with 95th percentile frequency
#
# usage:
#   ./klicova_slova.pl [-h] [-lN] [-cN] [-pN] [-v] [FILEPATH]
# 
# examples:
#   cat text.txt | ./klicova_slova.pl
#   ./klicova_slova.pl text.txt
#   ./klicova_slova.pl -p90 -l4 ./doc/intro_to_perl.txt
#   ./klicova_slova.pl ./doc/sample.txt -c1 -l4
###########################################################


use strict;
use warnings;
use utf8;


# static globals
my $usage = "usage: $0 [-h] [-lN] [-cN] [-pN] [-v] [FILEPATH]";
my $default_perc = 95;
my $ignore_path = "./ignore_list.txt";

# options
my %ignore;
my $path;
my $min_len = 3;
my $cut_off;
my $percentile;
my $verbose;

# global word frequency hash
my %key_words;


parse_args(); # parses arguments and sets option variables

load_ignores(); # load list of words to ignore

# get word frequency
if (defined $path) {
    open(IN, '<:encoding(UTF-8)', $path) or die $!;
    while (<IN>) {
        for my $word (split(/\W+/, $_)) {
            next if (length($word) < $min_len);
            $key_words{lc($word)} += 1;
        }
    }
} else {
    binmode(STDIN, ":utf8"); # console encoding
    while (<STDIN>) {
        for my $word (split(/\W+/, $_)) {
            next if (length($word) < $min_len);
            $key_words{lc($word)} += 1;
        }
    }
}

# set cut off to a percentile if '-c' is not used or if '-p' is used
if (not defined $cut_off or defined $percentile) {
    $percentile = defined $percentile ? $percentile : $default_perc;
    my $perc_index = (scalar values %key_words) * $percentile / 100;
    $cut_off = (sort { $a <=> $b } values(%key_words))[$perc_index];
}

# output of keywords
binmode(STDOUT, ":utf8"); # console encoding
for my $k (sort { $key_words{$b} <=> $key_words{$a} } keys(%key_words)) {
    last if ($key_words{$k} < $cut_off);
    next if (exists $ignore{$k});
    print "$k";
    print ": $key_words{$k}" if ($verbose);
    print "\n";
}

close(IN);

exit 0;



# prints help message and exits
sub print_help {
    print $usage . "\n" .
    "if no FILEPATH is given it will read from STDIN" .
    "It analyzes a text file and atempts to find its keywords,\n" .
    "which are then printed out from the most to the least significant.\n" .
    "It ignores words from $ignore_path if it exits and\n" .
    "by default it ignores 2 or 1 letter words and shows only\n" .
    "words with 95th percentile frequency" .
    "options:\n" .
        "\t-lN\tshow only words of length N or higher\n" .
        "\t-cN\tshow only words with occurance of N or higher\n" .
        "\t-pN\tshow only words with Nth percentile occurance or higher\n" .
            "\t\t\t(overwrights -c option)\n" .
        "\t-v\tshow the number of occurences for each key word\n" .
        "\t-h\tshow this message\n";
    exit 0;
}

# parse arguments
sub parse_args {
    for my $arg (@ARGV) {
        if ($arg eq "-h") {
            print_help(); # exits the program
        } elsif ($arg eq "-v") {
            $verbose = 1;
        } elsif ($arg =~ /-l(\d+)/) {
            $min_len = $1;
        } elsif ($arg =~ /-c(\d+)/) {
            $cut_off = $1;
        } elsif ($arg =~ /-p(\d+)/) {
            $percentile = $1;
            if ($percentile > 99) {
                print "can't get $percentile" . "th percentile\n";
                print "choose a whole number from 0 to 99\n";
                exit 1;
            }
        } elsif (not defined $path) {
            $path = $arg;
        } else {
            print $usage . "\n";
            exit 1;
        }
    }
}

sub load_ignores {
    open(IGNORE, '<:encoding(UTF-8)', $ignore_path) or return;

    while (<IGNORE>) {
        chomp;  # avoid \n on last field
        next if (length($_) < $min_len);
        $ignore{lc($_)} = 1;
    }
    
    close(IGNORE);
}
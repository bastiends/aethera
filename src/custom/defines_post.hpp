// Copyright (c) rAthena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder

#ifndef CONFIG_CUSTOM_DEFINES_POST_HPP
#define CONFIG_CUSTOM_DEFINES_POST_HPP

/**
 * rAthena configuration file (http://rathena.org)
 * For detailed guidance on these check http://rathena.org/wiki/SRC/config/
 **/

// Disable packet obfuscation: avoids needing client-specific
// PACKET_OBFUSCATION_KEY1/2/3, which change per kRO client build and
// aren't published for every release. Client side must match: enable
// the "Disable Login/Char packet encryption" and "Disable Map packet
// encryption" patches (NoEncrForLC, NoPacketEncr).
#undef PACKET_OBFUSCATION

#endif /* CONFIG_CUSTOM_DEFINES_POST_HPP */
